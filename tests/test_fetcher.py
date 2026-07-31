from unittest.mock import MagicMock, patch

import pytest
import requests

from dataharvest.config import Config
from dataharvest.fetcher import Fetcher, FetchError


def make_config(tmp_path):
    p = tmp_path / "cfg.yaml"
    p.write_text(
        """
url: https://example.com
pagination: {}
selectors:
  titre: h1
fetcher:
  delay: 0.01
  retries: 2
  timeout: 5
  user_agent: TestAgent/1.0
store:
  backend: json
  path: output/x.json
""",
        encoding="utf-8",
    )
    return Config(str(p))


def test_fetch_returns_non_empty_str(tmp_path):
    config = make_config(tmp_path)
    fetcher = Fetcher(config)

    fake_resp = MagicMock(status_code=200, text="<html>ok</html>")
    fake_resp.raise_for_status = MagicMock()

    with patch("requests.Session.get", return_value=fake_resp):
        html = fetcher.fetch("https://example.com")

    assert isinstance(html, str)
    assert len(html) > 0


def test_fetch_raises_fetcherror_after_retries(tmp_path):
    config = make_config(tmp_path)
    fetcher = Fetcher(config)

    with patch("requests.Session.get", side_effect=requests.exceptions.ConnectionError("boom")):
        with pytest.raises(FetchError):
            fetcher.fetch("https://example.com")


def test_fetch_uses_configured_user_agent(tmp_path):
    config = make_config(tmp_path)
    fetcher = Fetcher(config)
    assert fetcher.session.headers["User-Agent"] == "TestAgent/1.0"


def test_fetch_all_respects_delay(tmp_path):
    config = make_config(tmp_path)
    fetcher = Fetcher(config)

    fake_resp = MagicMock(status_code=200, text="ok")
    fake_resp.raise_for_status = MagicMock()

    with patch("requests.Session.get", return_value=fake_resp):
        results = fetcher.fetch_all(["https://example.com/1", "https://example.com/2"])

    assert len(results) == 2