# dataharvest/config.py

import json
import os
from types import SimpleNamespace

import yaml

REQUIRED_KEYS = ("url", "pagination", "selectors", "fetcher", "store")

DEFAULT_FETCHER = {
    "delay": 1.0,
    "retries": 3,
    "timeout": 15,
    "user_agent": "DataHarvest/1.0",
}

DEFAULT_PAGINATION = {
    "pattern": None,
    "start": 1,
    "max_pages": 1,
}


def _to_namespace(value):
    if isinstance(value, dict):
        return SimpleNamespace(**{k: _to_namespace(v) for k, v in value.items()})
    return value


class Config:
    """Charge un fichier YAML ou JSON et expose ses valeurs sous forme d'attributs."""

    def __init__(self, path: str):
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Fichier de configuration introuvable: {path}")

        self.path = path
        raw = self._load(path)

        missing = [key for key in REQUIRED_KEYS if key not in raw]
        if missing:
            raise ValueError(
                f"Cle(s) obligatoire(s) manquante(s) dans {path}: {', '.join(missing)}"
            )

        self.url = raw["url"]
        self.selectors = dict(raw["selectors"])

        pagination = {**DEFAULT_PAGINATION, **raw["pagination"]}
        self.pagination = _to_namespace(pagination)

        fetcher = {**DEFAULT_FETCHER, **raw["fetcher"]}
        fetcher["delay"] = float(fetcher["delay"])
        self.fetcher = _to_namespace(fetcher)

        self.store = _to_namespace(raw["store"])

    @staticmethod
    def _load(path: str) -> dict:
        ext = os.path.splitext(path)[1].lower()
        with open(path, "r", encoding="utf-8") as f:
            if ext in (".yaml", ".yml"):
                data = yaml.safe_load(f)
            elif ext == ".json":
                data = json.load(f)
            else:
                raise ValueError(f"Extension de configuration non supportee: {ext}")
        if not isinstance(data, dict):
            raise ValueError(f"Le fichier de configuration {path} doit contenir un objet cle/valeur")
        return data
