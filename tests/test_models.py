"""Declarative decoding of API payloads into models."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from dreep import (
    Asset,
    ConvertedDocument,
    DreepError,
    FolderListing,
    MediaPage,
    OCRResult,
    PresignedUpload,
    Usage,
)
from dreep._decode import camel_case
from tests.support import ASSET_ID, asset_payload


@pytest.mark.parametrize(
    ("name", "expected"),
    [("id", "id"), ("size_bytes", "sizeBytes"), ("access_control_type", "accessControlType")],
)
def test_camel_case(name: str, expected: str) -> None:
    assert camel_case(name) == expected


def test_asset_decodes_and_coerces() -> None:
    asset = Asset._from_api(asset_payload())
    assert asset.id == ASSET_ID
    assert asset.size_bytes == 245000  # the API sends a string
    assert asset.original_filename == "hero.jpg"
    assert asset.created_at == datetime(2026, 8, 16, 18, 53, 29, tzinfo=timezone.utc)
    assert asset.raw["mimetype"] == "image/webp"


def test_bigint_strings_keep_every_digit() -> None:
    assert Usage._from_api({"storageBytes": "9007199254740993"}).storage_bytes == 9007199254740993


def test_missing_optional_fields_become_none() -> None:
    asset = Asset._from_api({"id": "a", "url": "https://x/y"})
    assert asset.width is None
    assert asset.size_bytes == 0
    assert asset.created_at is None


@pytest.mark.parametrize("payload", [{"url": "https://x"}, {"id": "", "url": "u"}, ["not", "obj"]])
def test_missing_required_fields_raise(payload: object) -> None:
    with pytest.raises(DreepError, match="Unexpected response"):
        Asset._from_api(payload)


def test_unparseable_values_degrade_to_none() -> None:
    asset = Asset._from_api(
        {"id": "a", "url": "u", "width": "wide", "createdAt": "yesterday", "status": 5}
    )
    assert (asset.width, asset.created_at, asset.status) == (None, None, None)


def test_media_page_maps_type_to_mimetype_and_nests() -> None:
    page = MediaPage._from_api(
        {
            "assets": [{"id": "a", "url": "u", "type": "image/png", "sizeBytes": "7"}, "junk"],
            "pagination": {"page": 1, "limit": 20, "total": 1},
        }
    )
    assert [item.mimetype for item in page] == ["image/png"]
    assert page.assets[0].size_bytes == 7
    assert page.pagination is not None
    assert page.pagination.total == 1
    assert len(page) == 1


def test_folder_listing_with_current_folder() -> None:
    listing = FolderListing._from_api(
        {"folders": [{"id": "f", "path": "a/b", "parentId": None}], "currentFolder": {"id": "p"}}
    )
    assert [f.path for f in listing] == ["a/b"]
    assert listing.current_folder is not None
    assert listing.current_folder.id == "p"


def test_presigned_upload_bool_coercion() -> None:
    upload = PresignedUpload._from_api({"id": "u", "alreadyExists": "true"})
    assert upload.already_exists is True
    assert upload.upload_url is None


def test_ocr_result_and_converted_document() -> None:
    ocr = OCRResult._from_api({"text": "hi", "blocks": [{"Page": 1}], "savedAsset": None})
    assert (ocr.text, ocr.blocks, ocr.saved_asset) == ("hi", [{"Page": 1}], None)
    doc = ConvertedDocument._from_api({"id": "d", "url": "u", "status": "processing"})
    assert doc.is_ready is False


def test_models_are_frozen() -> None:
    asset = Asset._from_api(asset_payload())
    with pytest.raises(AttributeError):
        asset.id = "other"  # type: ignore[misc]
