# dataharvest/store.py

import csv
import json
import os
import re
import sqlite3

_SAFE_COLUMN_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


class Store:
    """Persiste les items valides sur l'un des trois backends supportes."""

    BACKENDS = ("csv", "sqlite", "json")

    def __init__(self, backend: str, path: str):
        if backend not in self.BACKENDS:
            raise ValueError(f"Backend inconnu: {backend}")
        self.backend = backend
        self.path = path

        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)

    def save(self, items: list[dict]) -> int:
        if not items:
            return 0
        if self.backend == "csv":
            return self._save_csv(items)
        if self.backend == "sqlite":
            return self._save_sqlite(items)
        return self._save_json(items)

    def count(self) -> int:
        if self.backend == "csv":
            if not os.path.isfile(self.path):
                return 0
            with open(self.path, "r", encoding="utf-8", newline="") as f:
                return sum(1 for _ in csv.reader(f)) - 1 if os.path.getsize(self.path) else 0
        if self.backend == "sqlite":
            if not os.path.isfile(self.path) or not self._sqlite_table_exists():
                return 0
            with sqlite3.connect(self.path) as conn:
                return conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        return len(self._read_json())

    def export_to(self, other_backend: str, path: str) -> int:
        items = self._read_all()
        target = Store(other_backend, path)
        return target.save(items)

    # -- csv --------------------------------------------------------------

    def _save_csv(self, items: list[dict]) -> int:
        existing_urls = self._existing_csv_urls()
        new_items = [item for item in items if item.get("url") not in existing_urls]
        if not new_items:
            return 0

        is_new_file = not os.path.isfile(self.path) or os.path.getsize(self.path) == 0
        fieldnames = self._csv_fieldnames(new_items)

        with open(self.path, "a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if is_new_file:
                writer.writeheader()
            for item in new_items:
                writer.writerow({field: item.get(field, "") for field in fieldnames})
        return len(new_items)

    def _existing_csv_urls(self) -> set:
        if not os.path.isfile(self.path):
            return set()
        with open(self.path, "r", encoding="utf-8", newline="") as f:
            return {row.get("url") for row in csv.DictReader(f)}

    def _csv_fieldnames(self, new_items: list[dict]) -> list:
        if os.path.isfile(self.path) and os.path.getsize(self.path) > 0:
            with open(self.path, "r", encoding="utf-8", newline="") as f:
                header = next(csv.reader(f), None)
            if header:
                return header
        fieldnames = []
        for item in new_items:
            for key in item.keys():
                if key not in fieldnames:
                    fieldnames.append(key)
        return fieldnames

    # -- sqlite -------------------------------------------------------------
    #
    # Le schema n'est pas fixe a l'avance : les colonnes sont derivees des cles
    # des items rencontres, pour supporter des sites aux champs tres differents
    # (ex: titre/prix/note pour un catalogue, nom/version/auteur pour pypi.org).

    def _sqlite_table_exists(self) -> bool:
        with sqlite3.connect(self.path) as conn:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='items'"
            ).fetchone()
            return row is not None

    def _sqlite_columns(self, conn) -> set:
        return {row[1] for row in conn.execute("PRAGMA table_info(items)")}

    def _ensure_sqlite_schema(self, conn, fields: list):
        columns = [f for f in dict.fromkeys(fields) if _SAFE_COLUMN_RE.match(f)]
        if "url" not in columns:
            columns.append("url")

        if not self._sqlite_table_exists():
            column_defs = ", ".join(f'"{c}" TEXT' for c in columns if c != "url")
            sep = ", " if column_defs else ""
            conn.execute(
                f'CREATE TABLE items (id INTEGER PRIMARY KEY AUTOINCREMENT, '
                f'"url" TEXT UNIQUE{sep}{column_defs})'
            )
        else:
            existing = self._sqlite_columns(conn)
            for col in columns:
                if col not in existing:
                    conn.execute(f'ALTER TABLE items ADD COLUMN "{col}" TEXT')

    def _save_sqlite(self, items: list[dict]) -> int:
        fields = []
        for item in items:
            for key in item.keys():
                if key not in fields:
                    fields.append(key)

        inserted = 0
        with sqlite3.connect(self.path) as conn:
            self._ensure_sqlite_schema(conn, fields)
            columns = sorted(self._sqlite_columns(conn) - {"id"})
            placeholders = ", ".join("?" for _ in columns)
            column_list = ", ".join(f'"{c}"' for c in columns)
            for item in items:
                values = [item.get(c, "") for c in columns]
                cur = conn.execute(
                    f'INSERT OR IGNORE INTO items ({column_list}) VALUES ({placeholders})',
                    values,
                )
                inserted += cur.rowcount
            conn.commit()
        return inserted

    # -- json -----------------------------------------------------------------

    def _save_json(self, items: list[dict]) -> int:
        existing = self._read_json()
        existing_urls = {item.get("url") for item in existing}
        new_items = [item for item in items if item.get("url") not in existing_urls]
        combined = existing + new_items
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(combined, f, ensure_ascii=False, indent=2)
        return len(new_items)

    def _read_json(self) -> list:
        if not os.path.isfile(self.path) or os.path.getsize(self.path) == 0:
            return []
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    # -- shared ---------------------------------------------------------------

    def _read_all(self) -> list[dict]:
        if self.backend == "csv":
            if not os.path.isfile(self.path):
                return []
            with open(self.path, "r", encoding="utf-8", newline="") as f:
                return list(csv.DictReader(f))
        if self.backend == "sqlite":
            if not os.path.isfile(self.path) or not self._sqlite_table_exists():
                return []
            with sqlite3.connect(self.path) as conn:
                conn.row_factory = sqlite3.Row
                columns = sorted(self._sqlite_columns(conn) - {"id"})
                column_list = ", ".join(f'"{c}"' for c in columns)
                rows = conn.execute(f"SELECT {column_list} FROM items").fetchall()
                return [dict(row) for row in rows]
        return self._read_json()
