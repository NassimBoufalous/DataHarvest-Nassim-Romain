# dataharvest/pipeline.py

import re
from abc import ABC, abstractmethod
from urllib.parse import urljoin

from bs4 import BeautifulSoup

_ATTR_SELECTOR_RE = re.compile(r"\[([a-zA-Z_:-]+)\]\s*$")


class BasePipeline(ABC):
    @abstractmethod
    def process(self, html: str) -> list[dict]:
        """Retourne TOUJOURS une liste, jamais None."""

    @abstractmethod
    def next_page_url(self, html: str, current_url: str) -> str | None:
        """Retourne l'URL de la page suivante ou None si fin."""


class GenericPipeline(BasePipeline):
    """Extrait des items structures du HTML brut a partir de selecteurs CSS.

    Le nombre d'items est determine par le selecteur le plus fourni (en general
    celui du champ 'titre'). Pour un champ absent sur un item donne, la valeur
    retournee est une chaine vide plutot qu'une exception.
    """

    def __init__(self, selectors: dict, base_url: str = None):
        self.selectors = dict(selectors)
        self.base_url = base_url
        self._seen_urls = {}

    def process(self, html: str) -> list[dict]:
        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        matches = {field: soup.select(selector) for field, selector in self.selectors.items()}

        # Le nombre d'items est celui du champ PRIMAIRE (le premier declare
        # dans la config, generalement 'titre'), pas le champ qui remonte le
        # plus d'elements : un champ secondaire peut naturellement matcher
        # plusieurs elements par item (ex: plusieurs tags par citation).
        primary_field = next(iter(self.selectors), None)
        count = len(matches.get(primary_field, [])) if primary_field else 0
        if count == 0:
            return []

        items = []
        for i in range(count):
            item = {}
            for field, selector in self.selectors.items():
                elements = matches[field]
                element = elements[i] if i < len(elements) else None
                item[field] = self._extract(element, selector, field)
            items.append(item)

        self._dedupe_urls(items)
        return items

    def next_page_url(self, html: str, current_url: str) -> str | None:
        return None

    def _extract(self, element, selector: str, field_name: str) -> str:
        if element is None:
            return ""

        if field_name == "url":
            href = element.get("href")
            if href:
                return urljoin(self.base_url, href) if self.base_url else href

        attr_match = _ATTR_SELECTOR_RE.search(selector)
        if attr_match:
            attr_name = attr_match.group(1)
            value = element.get(attr_name)
            if isinstance(value, list):
                selector_classes = set(re.findall(r"\.([a-zA-Z0-9_-]+)", selector))
                value = " ".join(token for token in value if token not in selector_classes) or " ".join(value)
            if value:
                return value

        return element.get_text(strip=True)

    def _dedupe_urls(self, items: list) -> None:
        """Distingue par un fragment #N les items qui partagent la meme url.

        Certains sites (ex: quotes.toscrape.com) n'exposent pas d'URL propre a
        chaque item et renvoient plutot un lien partage (page auteur, tag...).
        Sans cela, le Store deduplique par url et perd des items pourtant
        distincts. Le compteur est garde au niveau de l'instance pour rester
        coherent d'une page a l'autre lors de la pagination.
        """
        for item in items:
            url = item.get("url")
            if not url:
                continue
            self._seen_urls[url] = self._seen_urls.get(url, 0) + 1
            if self._seen_urls[url] > 1:
                item["url"] = f"{url}#{self._seen_urls[url]}"


class PaginationPipeline(GenericPipeline):
    """Etend GenericPipeline avec la construction de l'URL de la page suivante."""

    def __init__(self, selectors: dict, pagination_config, base_url: str = None):
        super().__init__(selectors, base_url=base_url)
        self.pagination_config = pagination_config
        self._current_page = getattr(pagination_config, "start", 1)

    def next_page_url(self, html: str, current_url: str) -> str | None:
        pattern = getattr(self.pagination_config, "pattern", None)
        if not pattern:
            return None

        # Verifie seulement qu'il reste des items (via le selecteur principal),
        # sans rappeler process() en entier : celui-ci a deja ete invoque par
        # l'appelant pour cette page et a des effets de bord (dedoublonnage).
        primary_selector = next(iter(self.selectors.values()), None)
        if not primary_selector:
            return None
        soup = BeautifulSoup(html, "lxml")
        if not soup.select(primary_selector):
            return None

        max_pages = getattr(self.pagination_config, "max_pages", 1)
        next_page = self._current_page + 1
        if next_page > max_pages:
            return None

        self._current_page = next_page
        path = pattern.format(n=next_page)
        return urljoin(self.base_url or current_url, path)
