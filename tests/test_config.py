import pytest

from dataharvest.config import Config

VALID_YAML = """
url: https://example.com/
pagination:
  pattern: /page/{n}/
  start: 1
  max_pages: 5
selectors:
  titre: h2.post-title a
fetcher:
  delay: 2.5
  retries: 3
  timeout: 15
  user_agent: DataHarvest/1.0
store:
  backend: csv
  path: output/example.csv
"""


def test_config_raises_filenotfounderror_on_missing_file(tmp_path):
    missing_path = tmp_path / "does_not_exist.yaml"

    with pytest.raises(FileNotFoundError):
        Config(str(missing_path))


def test_config_raises_valueerror_on_missing_required_key(tmp_path):
    incomplete_yaml = """
url: https://example.com/
selectors:
  titre: h2.post-title a
"""
    config_path = tmp_path / "incomplete.yaml"
    config_path.write_text(incomplete_yaml, encoding="utf-8")

    with pytest.raises(ValueError):
        Config(str(config_path))


def test_config_loads_valid_yaml(tmp_path):
    config_path = tmp_path / "valid.yaml"
    config_path.write_text(VALID_YAML, encoding="utf-8")

    config = Config(str(config_path))

    assert config.url == "https://example.com/"
    assert config.selectors == {"titre": "h2.post-title a"}
    assert config.fetcher.delay == 2.5
    assert isinstance(config.fetcher.delay, float)
    assert config.pagination.max_pages == 5
    assert config.store.backend == "csv"


def test_config_supports_json(tmp_path):
    import json

    data = {
        "url": "https://example.com/",
        "pagination": {"pattern": None, "start": 1, "max_pages": 1},
        "selectors": {"titre": "h2 a"},
        "fetcher": {"delay": 1.0, "retries": 3, "timeout": 15, "user_agent": "DataHarvest/1.0"},
        "store": {"backend": "json", "path": "output/example.json"},
    }
    config_path = tmp_path / "valid.json"
    config_path.write_text(json.dumps(data), encoding="utf-8")

    config = Config(str(config_path))

    assert config.url == "https://example.com/"
    assert config.fetcher.retries == 3
