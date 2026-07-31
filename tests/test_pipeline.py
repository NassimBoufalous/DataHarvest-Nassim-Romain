from types import SimpleNamespace

from dataharvest.pipeline import GenericPipeline, PaginationPipeline

LISTING_HTML = """
<html><body>
  <article class="card">
    <h2><a href="/item-1.html" title="Item One">Item One</a></h2>
    <p class="price">10 EUR</p>
  </article>
  <article class="card">
    <h2><a href="/item-2.html" title="Item Two">Item Two</a></h2>
  </article>
</body></html>
"""


def test_process_returns_list_on_empty_html():
    pipeline = GenericPipeline(selectors={"titre": "h2 a"})

    assert pipeline.process("") == []
    assert pipeline.process(None) == []


def test_process_does_not_raise_when_selector_matches_nothing():
    pipeline = GenericPipeline(selectors={"titre": "h2 a", "prix": "p.price"})

    items = pipeline.process(LISTING_HTML)

    assert len(items) == 2
    assert items[0]["prix"] == "10 EUR"
    assert items[1]["prix"] == ""  # p.price absent sur le 2e item, pas d'exception


def test_process_extracts_titre_and_url():
    pipeline = GenericPipeline(
        selectors={"titre": "h2 a", "url": "h2 a"},
        base_url="https://example.com/",
    )

    items = pipeline.process(LISTING_HTML)

    assert items[0]["titre"] == "Item One"
    assert items[0]["url"] == "https://example.com/item-1.html"
    assert items[1]["titre"] == "Item Two"


def test_pagination_stops_at_max_pages():
    pagination_config = SimpleNamespace(pattern="/page/{n}/", start=1, max_pages=2)
    pipeline = PaginationPipeline(
        selectors={"titre": "h2 a"},
        pagination_config=pagination_config,
        base_url="https://example.com/",
    )

    next_url = pipeline.next_page_url(LISTING_HTML, "https://example.com/page/1/")
    assert next_url == "https://example.com/page/2/"

    # max_pages=2 atteint : plus de page suivante
    next_url = pipeline.next_page_url(LISTING_HTML, "https://example.com/page/2/")
    assert next_url is None


def test_pagination_stops_when_page_has_no_items():
    pagination_config = SimpleNamespace(pattern="/page/{n}/", start=1, max_pages=10)
    pipeline = PaginationPipeline(
        selectors={"titre": "h2 a"},
        pagination_config=pagination_config,
        base_url="https://example.com/",
    )

    next_url = pipeline.next_page_url("<html><body>vide</body></html>", "https://example.com/page/1/")

    assert next_url is None
