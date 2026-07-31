# dataharvest/fetcher.py
"""Telechargement HTTP orchestrant la chaine de middlewares."""

import time

import requests

from .middleware import RetryMiddleware


class FetchError(Exception):
    """Levee quand tous les retries sont epuises pour une URL."""


class Fetcher:
    def __init__(self, config, middlewares: list = None):
        self.config = config
        self.middlewares = middlewares or []
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config.fetcher.user_agent})

        self._retry_mw = next(
            (m for m in self.middlewares if isinstance(m, RetryMiddleware)), None
        )

    def fetch(self, url: str) -> str:
        """Retourne le HTML ou leve FetchError apres epuisement des retries."""
        max_retries = self._retry_mw.max_retries if self._retry_mw else self.config.fetcher.retries
        base_headers = dict(self.session.headers)
        last_exc = None

        attempt = 0
        while attempt <= max_retries:
            req_url, req_headers = url, dict(base_headers)
            for mw in self.middlewares:
                req_url, req_headers = mw.process_request(req_url, req_headers)

            try:
                response = self.session.get(
                    req_url, headers=req_headers, timeout=self.config.fetcher.timeout
                )
                for mw in self.middlewares:
                    response = mw.process_response(response)

                retry_needed = (
                    self._retry_mw.should_retry(response=response)
                    if self._retry_mw
                    else (response.status_code == 429 or 500 <= response.status_code < 600)
                )
                if retry_needed and attempt < max_retries:
                    time.sleep(self._backoff_delay(attempt))
                    attempt += 1
                    continue

                response.raise_for_status()
                return response.text

            except requests.RequestException as e:
                last_exc = e
                if attempt >= max_retries:
                    break
                time.sleep(self._backoff_delay(attempt))
                attempt += 1

        raise FetchError(
            f"Echec du fetch de {url} apres {max_retries} tentative(s) : {last_exc}"
        )

    def _backoff_delay(self, attempt: int) -> float:
        return self._retry_mw.backoff_delay(attempt) if self._retry_mw else (2 ** attempt)

    def fetch_all(self, urls: list) -> list:
        """Fetche une liste d'URLs en respectant config.fetcher.delay entre chaque."""
        results = []
        for i, url in enumerate(urls):
            results.append(self.fetch(url))
            if i < len(urls) - 1:
                time.sleep(self.config.fetcher.delay)
        return results