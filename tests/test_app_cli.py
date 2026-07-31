import json
from unittest.mock import patch

import pytest

from dataharvest.app import build_parser, _guess_backend, cmd_crawl, cmd_export, cmd_validate
from dataharvest.store import Store


def make_config_file(tmp_path, extra_store=None):
    p = tmp_path / "cfg.yaml"
    store = extra_store or {"backend": "json", "path": str(tmp_path / "out.json")}
    p.write_text(
        f"""
url: https://example.com/page-1.html
pagination:
  pattern: /page-{{n}}.html
  start: 1
  max_pages: 1
selectors:
  titre: h2.post a
  url: h2.post a
fetcher:
  delay: 0.01
  retries: 1
  timeout: 5
  user_agent: TestAgent/1.0
store:
  backend: {store["backend"]}
  path: {store["path"]}
""",
        encoding="utf-8",
    )
    return str(p)


def test_guess_backend():
    assert _guess_backend("out.csv") == "csv"
    assert _guess_backend("out.json") == "json"
    assert _guess_backend("out.db") == "sqlite"
    with pytest.raises(ValueError):
        _guess_backend("out.xls")


def test_parser_crawl_subcommand():
    parser = build_parser()
    args = parser.parse_args(["crawl", "--config", "configs/books.yaml", "--dry-run"])
    assert args.command == "crawl"
    assert args.dry_run is True


def test_parser_export_subcommand():
    parser = build_parser()
    args = parser.parse_args(["export", "--from", "a.db", "--to", "b.csv"])
    assert getattr(args, "from") == "a.db"
    assert args.to == "b.csv"


def test_cmd_validate_valid_config(tmp_path, capsys):
    cfg_path = make_config_file(tmp_path)
    parser = build_parser()
    args = parser.parse_args(["validate", "--config", cfg_path])
    cmd_validate(args)
    out = capsys.readouterr().out
    assert "Config valide" in out


def test_cmd_validate_invalid_config(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("url: https://x.com\n", encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args(["validate", "--config", str(bad)])
    with pytest.raises(SystemExit):
        cmd_validate(args)


def test_cmd_crawl_dry_run(tmp_path):
    cfg_path = make_config_file(tmp_path)
    parser = build_parser()
    args = parser.parse_args(["crawl", "--config", cfg_path, "--dry-run"])

    fake_html = '<h2 class="post"><a href="/a1">Titre</a></h2>'
    with patch("dataharvest.fetcher.Fetcher.fetch", return_value=fake_html):
        cmd_crawl(args)  # ne doit pas lever d'exception


def test_cmd_export(tmp_path):
    json_path = tmp_path / "a.json"
    csv_path = tmp_path / "b.csv"
    Store("json", str(json_path)).save([{"titre": "A", "url": "https://x.com"}])

    parser = build_parser()
    args = parser.parse_args(["export", "--from", str(json_path), "--to", str(csv_path)])
    cmd_export(args)
    assert csv_path.exists()