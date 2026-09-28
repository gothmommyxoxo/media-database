import enum


class MediaType(str, enum.Enum):
    MANGA = "MANGA"
    BOOK = "BOOK"
    COMIC_BOOK = "COMIC_BOOK"
    GRAPHIC_NOVEL = "GRAPHIC_NOVEL"
    VIDEO_GAME = "VIDEO_GAME"
    BLU_RAY = "BLU_RAY"
    DVD = "DVD"
    VHS = "VHS"
    VCD = "VCD"
    LASERDISC = "LASERDISC"
    CD = "CD"
    VINYL = "VINYL"
    CASSETTE = "CASSETTE"


class ItemSource(str, enum.Enum):
    SCANNED = "SCANNED"
    MANUAL = "MANUAL"


class Role(str, enum.Enum):
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
