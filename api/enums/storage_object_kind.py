"""The categories of the bucket's objects, read from their key prefix."""

from enum import Enum


class StorageObjectKind(str, Enum):
    """What an object of the bucket is, as the storage page files and filters it."""

    WEBSITE_VIDEO = "website_video"
    WEBSITE_THUMBNAIL = "website_thumbnail"
    WEBSITE_BACKGROUND = "website_background"
    ASSISTANT_VIDEO = "assistant_video"
    ASSISTANT_THUMBNAIL = "assistant_thumbnail"
    PRESENTER = "presenter"
    SUPPORT = "support"
    PROSPECT_PHOTO = "prospect_photo"
    ASSISTANT_PHOTO = "assistant_photo"
    ASSISTANT_DOCUMENT = "assistant_document"
    MANUAL = "manual"
    OTHER = "other"
