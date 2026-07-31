# dataharvest/orchestrator.py

import time

from dataharvest.config import Config
from dataharvest.fetcher import Fetcher
from dataharvest.middleware import LoggingMiddleware, RetryMiddleware
from dataharvest.pipeline import PaginationPipeline
from dataharvest.store import Store
from dataharvest.validator import Validator


class Orchestrator:
    """Assemble Fetcher, Pipeline, Validator et Store et pilote un scraping complet."""

    def __init__(self, config: Config):
        self.config = config
        self.fetcher = Fetcher(config, middlewares=[LoggingMiddleware(), RetryMiddleware(config)])
        self.pipeline = PaginationPipeline(config.selectors, config.pagination, base_url=config.url)
        self.validator = Validator(required_fields=["titre", "url"])
        self.store = Store(config.store.backend, config.store.path)

    def run(self, dry_run: bool = False) -> dict:
        start = time.perf_counter()

        if dry_run:
            html = self.fetcher.fetch(self.config.url)
            items = self.pipeline.process(html)
            for item in items:
                print(item)
            return self._build_report(
                fetched=1,
                valid=items,
                rejected=[],
                stored=0,
                duree_secondes=time.perf_counter() - start,
            )

        pages_scrapees = 0
        all_valid = []
        all_rejected = []
        items_stockes = 0

        current_url = self.config.url
        while current_url:
            html = self.fetcher.fetch(current_url)
            pages_scrapees += 1

            page_items = self.pipeline.process(html)
            valid_items, rejected_items = self.validator.validate(page_items)
            all_valid.extend(valid_items)
            all_rejected.extend(rejected_items)
            items_stockes += self.store.save(valid_items)

            next_url = self.pipeline.next_page_url(html, current_url)
            if next_url == current_url:
                break
            current_url = next_url
            if current_url:
                time.sleep(self.config.fetcher.delay)

        duree_secondes = time.perf_counter() - start
        return self._build_report(
            fetched=pages_scrapees,
            valid=all_valid,
            rejected=all_rejected,
            stored=items_stockes,
            duree_secondes=duree_secondes,
        )

    def _build_report(self, fetched: int, valid: list, rejected: list, stored: int, duree_secondes: float) -> dict:
        return {
            "pages_scrapees": fetched,
            "items_trouves": len(valid) + len(rejected),
            "items_valides": len(valid),
            "items_rejetes": len(rejected),
            "items_stockes": stored,
            "duree_secondes": round(duree_secondes, 2),
        }
