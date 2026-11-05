"""Wire-level constants shared by every part of the SDK.

Anything that names a path, a parameter, or a server-side table lives here, so a
change to the API touches one file rather than a scattering of string literals.
"""

from __future__ import annotations

import re
from typing import Final

# --------------------------------------------------------------------------- #
# Hosts and paths
# --------------------------------------------------------------------------- #

#: Production API host. Override only through the ``DREEP_API_URL`` environment
#: variable, which exists for local development against a dev server. It is
#: deliberately not a constructor argument: self-hosting is not a supported
#: deployment, and the delivery host comes from URLs the API returns anyway.
API_URL: Final = "https://api.dreep.cloud"
API_PREFIX: Final = "/api/v1"
#: Name of the logger the SDK writes to.
LOGGER_NAME: Final = "dreep"
ENV_API_URL: Final = "DREEP_API_URL"
ENV_API_KEY: Final = "DREEP_API_KEY"
ENV_SIGNING_SECRET: Final = "DREEP_SIGNING_SECRET"  # noqa: S105 -- a variable name


class Path:
    """Endpoint paths, relative to :data:`API_PREFIX`."""

    UPLOAD: Final = "/upload"
    UPLOAD_PRESIGN: Final = "/upload/presign"
    MEDIA: Final = "/media"
    FOLDERS: Final = "/folders"
    PRESETS: Final = "/presets"
    OCR: Final = "/ocr"
    BG_REMOVE: Final = "/bg-remove"
    CONVERT: Final = "/convert"
    USAGE: Final = "/usage"

    @staticmethod
    def upload_confirm(upload_id: str) -> str:
        return f"{Path.UPLOAD}/{_segment(upload_id)}/confirm"

    @staticmethod
    def media(media_id: str) -> str:
        return f"{Path.MEDIA}/{_segment(media_id)}"

    @staticmethod
    def preset(preset_id: str) -> str:
        return f"{Path.PRESETS}/{_segment(preset_id)}"


def _segment(value: str) -> str:
    """Rejects ids that would change which endpoint a request reaches.

    An id is interpolated into a path, so ``"../usage"`` or ``"x?y"`` must never
    be sent as-is. Ids are UUIDs (or short ``med_`` style ids), so refusing
    anything with path or query syntax is strictly safer than escaping it.
    """
    if not isinstance(value, str) or not value:
        raise ValueError("An id must be a non-empty string.")
    if any(ch in value for ch in "/?#\\") or value in {".", ".."}:
        raise ValueError(f"Invalid id: {value!r}")
    return value


# --------------------------------------------------------------------------- #
# Timeouts and retries
# --------------------------------------------------------------------------- #

#: Seconds a JSON request waits before giving up. Uploads are exempt: a large
#: file legitimately takes longer than any default could anticipate.
DEFAULT_TIMEOUT: Final = 30.0
#: Retries after the first attempt, for idempotent (GET) requests only.
DEFAULT_MAX_RETRIES: Final = 2
#: Base delay for exponential backoff, in seconds.
RETRY_BASE_DELAY: Final = 0.25
#: Ceiling for any single retry wait, including one asked for by Retry-After.
RETRY_MAX_DELAY: Final = 8.0
#: Page size :meth:`Dreep.list_all_media` uses when the caller gives none.
DEFAULT_PAGE_SIZE: Final = 20
#: Attempts :meth:`Dreep.upload_presigned` makes at confirming while the bytes
#: settle in storage (the API answers 409 until they have).
CONFIRM_ATTEMPTS: Final = 5
#: Chunk size used when streaming file bytes to a presigned upload URL.
STREAM_CHUNK_SIZE: Final = 1024 * 1024

# --------------------------------------------------------------------------- #
# HTTP
# --------------------------------------------------------------------------- #


class Method:
    GET: Final = "GET"
    POST: Final = "POST"
    PUT: Final = "PUT"
    DELETE: Final = "DELETE"


class Header:
    AUTHORIZATION: Final = "Authorization"
    USER_AGENT: Final = "User-Agent"
    ACCEPT: Final = "Accept"
    CONTENT_TYPE: Final = "Content-Type"
    CONTENT_LENGTH: Final = "Content-Length"
    #: Lower-case: httpx response headers are case-insensitive, read as given.
    REQUEST_ID: Final = "x-request-id"
    RETRY_AFTER: Final = "retry-after"


AUTH_SCHEME: Final = "Bearer"
CONTENT_TYPE_JSON: Final = "application/json"
#: Schemes an absolute URL may use (CDN fetch URLs, presigned upload URLs).
URL_SCHEMES: Final = ("http", "https")
#: Multipart field carrying the file bytes.
FILE_FIELD: Final = "file"
#: Successful responses are wrapped as ``{message, code, data}``.
ENVELOPE_DATA: Final = "data"
#: bg-remove and convert wrap their result as ``{"asset": {...}}``.
ASSET_WRAPPER: Final = "asset"
#: ``GET /presets`` may answer with a bare list or ``{"presets": [...]}``.
PRESETS_WRAPPER: Final = "presets"
#: Literal value of ``parentId`` that asks for root folders only.
ROOT_PARENT_ID: Final = "null"
#: Connect timeout ceiling: a dead host should fail fast even for uploads.
CONNECT_TIMEOUT: Final = 10.0

# --------------------------------------------------------------------------- #
# Server-side validation rules mirrored for early, clear errors
# --------------------------------------------------------------------------- #

#: Preset keys the API accepts (verified against the live API).
PRESET_KEY_PATTERN: Final = re.compile(r"^[a-z0-9_]+$")
#: Separates path segments in folder paths and object keys.
PATH_SEPARATOR: Final = "/"
