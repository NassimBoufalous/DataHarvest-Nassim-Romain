from dataharvest.validator import Validator


def test_validate_rejects_missing_required_field():
    v = Validator(required_fields=["titre", "url"])
    items = [
        {"titre": "A", "url": "https://x.com"},
        {"titre": "", "url": "https://y.com"},
    ]
    valides, rejetes = v.validate(items)
    assert len(valides) == 1
    assert len(rejetes) == 1


def test_validate_rejects_invalid_url():
    v = Validator(required_fields=["titre", "url"])
    items = [{"titre": "A", "url": "pas-une-url"}]
    valides, rejetes = v.validate(items)
    assert len(valides) == 0
    assert len(rejetes) == 1


def test_validate_accepts_valid_items():
    v = Validator(required_fields=["titre", "url"])
    items = [{"titre": "A", "url": "https://x.com/page"}]
    valides, rejetes = v.validate(items)
    assert len(valides) == 1
    assert len(rejetes) == 0


def test_validate_min_lengths():
    v = Validator(required_fields=["titre"], min_lengths={"titre": 5})
    items = [{"titre": "Abc"}, {"titre": "Titre suffisamment long"}]
    valides, rejetes = v.validate(items)
    assert len(valides) == 1
    assert len(rejetes) == 1


def test_is_valid_url():
    v = Validator(required_fields=[])
    assert v.is_valid_url("https://example.com/page") is True
    assert v.is_valid_url("ftp://example.com") is False
    assert v.is_valid_url("") is False
    assert v.is_valid_url("example.com") is False