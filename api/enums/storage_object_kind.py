"""The categories of the bucket's objects, read from their key prefix."""

from enum import Enum


class StorageObjectKind(str, Enum):
    """What an object of the bucket is, as the storage page files and filters it (a product module adds its own)."""

    WEBSITE_VIDEO = "website_video"
    WEBSITE_THUMBNAIL = "website_thumbnail"
    WEBSITE_BACKGROUND = "website_background"
    PRESENTER = "presenter"
    SUPPORT = "support"
    PROSPECT_PHOTO = "prospect_photo"
    MANUAL = "manual"
    OTHER = "other"
