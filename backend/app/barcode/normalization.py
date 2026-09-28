def is_isbn13(barcode: str) -> bool:
    return len(barcode) == 13 and barcode[:3] in ("978", "979")


def normalize_barcode(raw: str) -> str:
    """Section 5.1.1: collapse zero-padded EAN-13 to its UPC-A equivalent so the same physical
    product isn't cached under two different keys. ISBN-13 values pass through unchanged.

    Full UPC-E -> UPC-A expansion is not implemented in this prototype (tracked as a follow-up);
    UPC-E values pass through as scanned.
    """
    cleaned = raw.strip()
    if len(cleaned) == 13 and cleaned.startswith("0") and not is_isbn13(cleaned):
        return cleaned[1:]
    return cleaned
