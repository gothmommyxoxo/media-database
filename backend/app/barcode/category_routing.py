"""Section 5.3 Step 4: when the general UPC lookup (Appendix A.1) returns a raw product title but
nothing classified it into a MediaType, its free-text category string is used to guess which
title-search providers are worth trying. This is deliberately a heuristic over free text (e.g.
UPCitemdb's "Media > Music & Sound Recordings > Music CDs"), not an exact classification.
"""

CATEGORY_KEYWORDS: list[tuple[str, list[str]]] = [
    ("movies", ["movie", "dvd", "blu-ray", "bluray", "film", "television", " tv "]),
    ("video_games", ["video game", "videogame", "games", "playstation", "xbox", "nintendo"]),
    ("comics", ["comic", "graphic novel"]),
    ("books", ["book", "manga"]),
]


def plausible_groups_for(category_hint: str | None) -> list[str]:
    if not category_hint:
        return []
    lowered = f" {category_hint.lower()} "
    return [group for group, keywords in CATEGORY_KEYWORDS if any(k in lowered for k in keywords)]
