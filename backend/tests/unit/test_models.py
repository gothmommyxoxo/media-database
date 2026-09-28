from app.models import ItemSource, MediaItem, MediaType, User


def test_create_user_and_media_item(db_session):
    user = User(username="alice", display_name="Alice", password_hash="hashed")
    db_session.add(user)
    db_session.commit()

    item = MediaItem(
        media_type=MediaType.CD,
        title="Discovery",
        barcode="724384960650",
        attributes={"artist": "Daft Punk"},
        external_ids={"musicbrainz": "abc-123"},
        source=ItemSource.SCANNED,
        added_by=user.id,
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)

    assert item.id is not None
    assert item.media_type == MediaType.CD
    assert item.attributes["artist"] == "Daft Punk"
    assert item.added_by == user.id
    assert item.created_at is not None


def test_barcode_has_no_uniqueness_constraint(db_session):
    user = User(username="bob", display_name="Bob", password_hash="hashed")
    db_session.add(user)
    db_session.commit()

    item_a = MediaItem(
        media_type=MediaType.MANGA,
        title="Volume 1",
        barcode="9781234567890",
        source=ItemSource.MANUAL,
        added_by=user.id,
    )
    item_b = MediaItem(
        media_type=MediaType.MANGA,
        title="A totally different book that collided on the same barcode",
        barcode="9781234567890",
        source=ItemSource.MANUAL,
        added_by=user.id,
    )
    db_session.add_all([item_a, item_b])
    db_session.commit()

    assert item_a.id != item_b.id
    assert item_a.barcode == item_b.barcode
