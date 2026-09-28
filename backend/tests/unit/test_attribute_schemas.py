import pytest
from pydantic import ValidationError

from app.attributes.schemas import validate_attributes
from app.models.enums import MediaType


def test_manga_attributes_validate_and_drop_none_fields():
    result = validate_attributes(MediaType.MANGA, {"series_title": "Berserk", "volume": 1})
    assert result == {"series_title": "Berserk", "volume": 1}


def test_cd_and_vinyl_share_music_attributes_schema():
    cd = validate_attributes(MediaType.CD, {"artist": "Daft Punk", "release_year": 2001})
    vinyl = validate_attributes(MediaType.VINYL, {"artist": "Daft Punk", "release_year": 2001})
    assert cd == vinyl == {"artist": "Daft Punk", "release_year": 2001}


def test_video_release_attributes_shared_across_five_types():
    for media_type in (
        MediaType.BLU_RAY,
        MediaType.DVD,
        MediaType.VHS,
        MediaType.VCD,
        MediaType.LASERDISC,
    ):
        result = validate_attributes(media_type, {"director": "Satoshi Kon", "is_anime": True})
        assert result == {"director": "Satoshi Kon", "is_anime": True}


def test_wrong_type_field_raises_validation_error():
    with pytest.raises(ValidationError):
        validate_attributes(MediaType.MANGA, {"volume": "not a number"})
