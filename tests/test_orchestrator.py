from types import SimpleNamespace
from unittest.mock import patch

from dataharvest.config import Config
from dataharvest.orchestrator import Orchestrator

ONE_PAGE_HTML = """
<html><body>
  <article class="card"><h2><a href="/item-1.html">Item One</a></h2></article>
  <article class="card"><h2><a href="/item-2.html">Item Two</a></h2></article>
</body></html>
"""


def make_config(tmp_path, backend="json"):
    config_path = tmp_path / "site.yaml"
    config_path.write_text(
        f"""
url: https://example.com/list/
pagination:
  pattern: null
  start: 1
  max_pages: 1
selectors:
  titre: h2 a
  url: h2 a
fetcher:
  delay: 0
  retries: 1
  timeout: 5
  user_agent: DataHarvest/1.0 (test)
store:
  backend: {backend}
  path: {tmp_path / "output.json"}
""",
        encoding="utf-8",
    )
    return Config(str(config_path))


def test_orchestrator_builds_all_components(tmp_path):
    config = make_config(tmp_path)

    orchestrator = Orchestrator(config)

    assert orchestrator.fetcher is not None
    assert orchestrator.pipeline is not None
    assert orchestrator.validator.required_fields == ["titre", "url"]
    assert orchestrator.store.backend == "json"


def test_run_returns_report_with_expected_keys(tmp_path):
    config = make_config(tmp_path)
    orchestrator = Orchestrator(config)

    with patch.object(orchestrator.fetcher, "fetch", return_value=ONE_PAGE_HTML):
        report = orchestrator.run()

    assert set(report.keys()) == {
        "pages_scrapees",
        "items_trouves",
        "items_valides",
        "items_rejetes",
        "items_stockes",
        "duree_secondes",
    }
    assert report["pages_scrapees"] == 1
    assert report["items_valides"] == 2
    assert report["items_rejetes"] == 0
    assert report["items_stockes"] == 2


def test_run_stores_items_via_store(tmp_path):
    config = make_config(tmp_path)
    orchestrator = Orchestrator(config)

    with patch.object(orchestrator.fetcher, "fetch", return_value=ONE_PAGE_HTML):
        orchestrator.run()

    assert orchestrator.store.count() == 2


def test_run_rejects_items_missing_required_fields(tmp_path):
    config_path = tmp_path / "no_url.yaml"
    config_path.write_text(
        f"""
url: https://example.com/list/
pagination:
  pattern: null
  start: 1
  max_pages: 1
selectors:
  titre: h2
  url: h2 a
fetcher:
  delay: 0
  retries: 1
  timeout: 5
  user_agent: DataHarvest/1.0 (test)
store:
  backend: json
  path: {tmp_path / "output_no_url.json"}
""",
        encoding="utf-8",
    )
    config = Config(str(config_path))
    orchestrator = Orchestrator(config)
    # 'titre' matche (h2 existe) mais 'url' non (pas de <a> dans le h2) :
    # l'item est bien produit par la Pipeline, mais avec url="" -> rejete par le Validator.
    html_missing_url = '<html><body><article class="card"><h2>Sans lien</h2></article></body></html>'

    with patch.object(orchestrator.fetcher, "fetch", return_value=html_missing_url):
        report = orchestrator.run()

    assert report["items_rejetes"] == 1
    assert report["items_valides"] == 0
    assert report["items_stockes"] == 0
