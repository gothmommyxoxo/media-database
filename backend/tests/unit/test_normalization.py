from app.barcode.normalization import is_isbn13, normalize_barcode


def test_zero_padded_ean13_normalizes_to_upc_a():
    assert normalize_barcode("0724384960650") == "724384960650"


def test_upc_a_passes_through_unchanged():
    assert normalize_barcode("724384960650") == "724384960650"


def test_isbn13_passes_through_unchanged_despite_leading_zero_rule():
    # ISBNs never start with "0" at this length (978/979 prefix), but guard the branch anyway.
    assert normalize_barcode("9781593070209") == "9781593070209"


def test_whitespace_is_stripped():
    assert normalize_barcode("  724384960650  ") == "724384960650"


def test_is_isbn13_detects_978_and_979_prefixes():
    assert is_isbn13("9781593070209")
    assert is_isbn13("9791234567896")
    assert not is_isbn13("724384960650")
