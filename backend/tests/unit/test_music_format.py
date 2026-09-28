import pytest

from app.barcode.music_format import map_music_format
from app.models.enums import MediaType


@pytest.mark.parametrize(
    "format_value,expected",
    [
        ("CD", MediaType.CD),
        ("Vinyl", MediaType.VINYL),
        ("Cassette", MediaType.CASSETTE),
        ("Digital Media", None),
        ("SACD", None),
        (None, None),
    ],
)
def test_map_music_format(format_value, expected):
    assert map_music_format(format_value) == expected
