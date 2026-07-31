import json
import sqlite3

import pytest

from dataharvest.store import Store

ITEM_1 = {"titre": "A", "url": "https://example.com/1"}
ITEM_2 = {"titre": "B", "url": "https://example.com/2"}


def test_store_raises_valueerror_on_unknown_backend(tmp_path):
    with pytest.raises(ValueError):
        Store("xml", str(tmp_path / "out.xml"))


def test_json_save_creates_valid_json_file(tmp_path):
    path = tmp_path / "items.json"
    store = Store("json", str(path))

    inserted = store.save([ITEM_1, ITEM_2])

    assert inserted == 2
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data == [ITEM_1, ITEM_2]


def test_sqlite_save_does_not_duplicate_same_url(tmp_path):
    path = tmp_path / "items.db"
    store = Store("sqlite", str(path))

    first = store.save([ITEM_1, ITEM_2])
    second = store.save([ITEM_1, ITEM_2])  # memes urls, doit etre ignore

    assert first == 2
    assert second == 0
    assert store.count() == 2

    with sqlite3.connect(path) as conn:
        rows = conn.execute("SELECT url FROM items").fetchall()
    assert len(rows) == 2


def test_csv_save_does_not_duplicate_same_url(tmp_path):
    path = tmp_path / "items.csv"
    store = Store("csv", str(path))

    first = store.save([ITEM_1, ITEM_2])
    second = store.save([ITEM_1])

    assert first == 2
    assert second == 0
    assert store.count() == 2


def test_export_to_transfers_all_items(tmp_path):
    csv_path = tmp_path / "items.csv"
    json_path = tmp_path / "exported.json"

    csv_store = Store("csv", str(csv_path))
    csv_store.save([ITEM_1, ITEM_2])

    exported = csv_store.export_to("json", str(json_path))

    assert exported == 2
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert {item["url"] for item in data} == {ITEM_1["url"], ITEM_2["url"]}
