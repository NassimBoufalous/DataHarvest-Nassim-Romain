import logging
from urllib.parse import urlparse

log = logging.getLogger("dataharvest.validator")


class Validator:
    def __init__(self, required_fields: list, min_lengths: dict = None):
        self.required_fields = required_fields
        self.min_lengths = min_lengths or {}

    def is_valid_url(self, url: str) -> bool:
        """True si l'URL commence par http(s):// et contient un domaine."""
        if not url:
            return False
        try:
            parsed = urlparse(url)
            return parsed.scheme in ("http", "https") and bool(parsed.netloc)
        except Exception:
            return False

    def validate(self, items: list) -> tuple:
        """Retourne (valides, rejetes)."""
        valides, rejetes = [], []

        for item in items:
            raison = self._raison_rejet(item)
            if raison:
                log.warning(f"Item rejete ({raison}) : {item}")
                rejetes.append(item)
            else:
                valides.append(item)

        return valides, rejetes

    def _raison_rejet(self, item: dict):
        for champ in self.required_fields:
            if not item.get(champ):
                return f"champ obligatoire manquant/vide : '{champ}'"

        if item.get("url") and not self.is_valid_url(item["url"]):
            return f"url invalide : '{item.get('url')}'"

        for champ, min_len in self.min_lengths.items():
            valeur = str(item.get(champ, ""))
            if len(valeur) < min_len:
                return f"'{champ}' trop court (< {min_len} caracteres)"

        return None