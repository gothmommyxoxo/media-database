from app.barcode.dedup import deduplicate
from app.barcode.schemas import BarcodeCandidate
from app.models.enums import MediaType


def test_same_provider_and_external_id_collapses():
    a = BarcodeCandidate(source_provider="musicbrainz", external_id="abc", title="Discovery")
    b = BarcodeCandidate(source_provider="musicbrainz", external_id="abc", title="Discovery (dup)")

    result = deduplicate([a, b])

    assert len(result) == 1
    assert result[0].title == "Discovery"


def test_same_title_and_media_type_across_providers_collapses():
    a = BarcodeCandidate(source_provider="musicbrainz", title="Discovery", media_type=MediaType.CD)
    b = BarcodeCandidate(source_provider="discogs", title="discovery", media_type=MediaType.CD)

    result = deduplicate([a, b])

    assert len(result) == 1


def test_same_title_but_different_media_type_is_kept_distinct():
    a = BarcodeCandidate(source_provider="musicbrainz", title="Discovery", media_type=MediaType.CD)
    b = BarcodeCandidate(source_provider="musicbrainz", title="Discovery", media_type=MediaType.VINYL)

    result = deduplicate([a, b])

    assert len(result) == 2


def test_candidates_with_no_external_id_and_no_title_overlap_are_all_kept():
    candidates = [
        BarcodeCandidate(source_provider="p1", title="A"),
        BarcodeCandidate(source_provider="p2", title="B"),
    ]

    assert len(deduplicate(candidates)) == 2


def test_unclassified_candidates_with_the_same_title_are_not_collapsed():
    # Regression: a general-UPC-provider raw stub and a Step 4 (5.3) title-search enrichment
    # routinely share a title while both are unclassified (media_type=None). They must not be
    # treated as duplicates -- that would silently discard whichever one Step 4 was adding.
    stub = BarcodeCandidate(source_provider="upcitemdb", title="Brazil", media_type=None)
    enriched = BarcodeCandidate(source_provider="tmdb", title="Brazil", media_type=None)

    result = deduplicate([stub, enriched])

    assert len(result) == 2
    assert {c.source_provider for c in result} == {"upcitemdb", "tmdb"}
