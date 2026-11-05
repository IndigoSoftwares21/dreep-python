"""The official Python SDK for Dreep -- media storage, transformation and delivery.

    from pathlib import Path
    from dreep import Dreep

    client = Dreep()  # reads DREEP_API_KEY
    asset = client.upload(Path("hero.jpg"), folder="marketing/2026")
    client.url(asset, {"width": 400, "format": "webp"})

See https://docs.dreep.cloud for the API reference.
"""

from __future__ import annotations

from ._async_client import AsyncDreep
from ._client import Dreep
from ._config import NOT_GIVEN
from ._errors import (
    DreepAPIError,
    DreepAuthError,
    DreepConflictError,
    DreepConnectionError,
    DreepError,
    DreepLimitError,
    DreepNotFoundError,
    DreepProcessingError,
    DreepRateLimitError,
    DreepServerError,
    DreepTimeoutError,
    DreepValidationError,
)
from ._version import __version__
from .types import (
    Asset,
    BackgroundRemovedAsset,
    ConvertedDocument,
    Folder,
    FolderListing,
    MediaItem,
    MediaPage,
    OCRResult,
    Pagination,
    Preset,
    PresignedUpload,
    SavedTextAsset,
    Transform,
    Usage,
)

__all__ = [
    "NOT_GIVEN",
    "Asset",
    "AsyncDreep",
    "BackgroundRemovedAsset",
    "ConvertedDocument",
    "Dreep",
    "DreepAPIError",
    "DreepAuthError",
    "DreepConflictError",
    "DreepConnectionError",
    "DreepError",
    "DreepLimitError",
    "DreepNotFoundError",
    "DreepProcessingError",
    "DreepRateLimitError",
    "DreepServerError",
    "DreepTimeoutError",
    "DreepValidationError",
    "Folder",
    "FolderListing",
    "MediaItem",
    "MediaPage",
    "OCRResult",
    "Pagination",
    "Preset",
    "PresignedUpload",
    "SavedTextAsset",
    "Transform",
    "Usage",
    "__version__",
]
