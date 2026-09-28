import pytest

from app.barcode.category_routing import plausible_groups_for


@pytest.mark.parametrize(
    "category_hint,expected",
    [
        ("Media > Music & Sound Recordings > Music CDs", []),
        ("Movies & TV > Blu-ray", ["movies"]),
        ("Video Games > PlayStation 5", ["video_games"]),
        ("Media > Books > Comics & Graphic Novels", ["comics", "books"]),
        (None, []),
        ("", []),
    ],
)
def test_plausible_groups_for(category_hint, expected):
    assert plausible_groups_for(category_hint) == expected
