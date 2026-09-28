from app.barcode.schemas import BarcodeCandidate


def deduplicate(candidates: list[BarcodeCandidate]) -> list[BarcodeCandidate]:
    """Section 5.3.1: two candidates are the same item if they share a provider AND external_id,
    or if they share a normalized title AND media_type across different providers.

    The title+media_type rule only applies once media_type is actually known. Two unclassified
    (media_type=None) candidates sharing a title are NOT treated as duplicates: the general UPC
    provider's raw stub and a Step 4 title-search result (5.3) routinely share the same raw title
    while one is unclassified, and collapsing them would silently discard whichever one Step 4 was
    supposed to add -- an absent classification is not evidence they're the same item.
    """
    seen_by_provider_id: set[tuple[str, str]] = set()
    seen_by_title: set[tuple[str, object]] = set()
    result: list[BarcodeCandidate] = []

    for candidate in candidates:
        id_key = (candidate.source_provider, candidate.external_id) if candidate.external_id else None
        title_key = (
            (candidate.title.strip().lower(), candidate.media_type)
            if candidate.title and candidate.media_type is not None
            else None
        )

        if id_key is not None and id_key in seen_by_provider_id:
            continue
        if title_key is not None and title_key in seen_by_title:
            continue

        if id_key is not None:
            seen_by_provider_id.add(id_key)
        if title_key is not None:
            seen_by_title.add(title_key)
        result.append(candidate)

    return result
