"""The synchronous client against an in-memory transport.

Covers what reaches the wire (method, path, auth, body) and what comes back.
The async client is generated from the same source; test_async_client.py
checks that it behaves identically on representative paths.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

import dreep
from dreep import Dreep
from tests.support import (
    API_BASE,
    API_KEY,
    ASSET_ID,
    CDN_BASE,
    Recorder,
    asset_payload,
    body_json,
    envelope,
    form_fields,
)

MakeClient = Callable[..., Dreep]


def test_requires_an_api_key() -> None:
    with pytest.raises(dreep.DreepError, match="API key"):
        Dreep()


def test_reads_key_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DREEP_API_KEY", API_KEY)
    with Dreep() as client:
        assert "0123" not in repr(client)  # the key is masked
        assert repr(client).startswith("Dreep(api_key='drp_test_")


def test_upload_sends_multipart_with_auth_and_transform(make_client: MakeClient) -> None:
    rec = Recorder(envelope(asset_payload()))
    asset = make_client(rec).upload(
        b"bytes",
        filename="hero.jpg",
        folder="marketing/2026",
        auto_create_folders=False,
        transform={"width": 800, "format": "webp", "trim_start": 1.5},
        preset_key="thumb",
    )
    request = rec.last
    assert (request.method, str(request.url)) == ("POST", f"{API_BASE}/upload")
    assert request.headers["authorization"] == f"Bearer {API_KEY}"
    assert request.headers["user-agent"].startswith("dreep-python/")
    assert form_fields(request) == {
        "width": "800",
        "format": "webp",
        "trimStart": "1.5",
        "p": "thumb",
        "folder": "marketing/2026",
        "autoCreateFolders": "false",
    }
    assert b'filename="hero.jpg"' in request.content
    assert (asset.id, asset.size_bytes) == (ASSET_ID, 245000)


def test_presign_and_confirm_send_json(make_client: MakeClient) -> None:
    rec = Recorder(
        envelope({"id": "up1", "uploadUrl": "https://cdn/u", "alreadyExists": False}, 201),
        envelope(asset_payload()),
    )
    client = make_client(rec)
    upload = client.presign_upload(content_type="video/mp4", size_bytes=10, key="a/b.mp4")
    client.confirm_upload(upload.id, transform={"width": 10, "preset": "p1"})
    presign, confirm = rec.requests
    assert body_json(presign) == {"contentType": "video/mp4", "sizeBytes": 10, "key": "a/b.mp4"}
    assert str(confirm.url) == f"{API_BASE}/upload/up1/confirm"
    assert body_json(confirm) == {"transform": {"width": 10, "preset": "p1"}}


def test_upload_presigned_streams_without_auth_and_retries_confirm(
    make_client: MakeClient, tmp_path: Path
) -> None:
    path = tmp_path / "clip.mp4"
    path.write_bytes(b"x" * 10)
    rec = Recorder(
        envelope({"id": "up1", "uploadUrl": "https://storage.example/put/up1"}, 201),
        httpx.Response(200),
        httpx.Response(409, json={"message": "not yet"}),
        envelope(asset_payload()),
    )
    asset = make_client(rec).upload_presigned(path, folder="clips")
    presign, put, *_ = rec.requests
    assert body_json(presign) == {
        "contentType": "video/mp4",
        "sizeBytes": 10,
        "filename": "clip.mp4",
        "folder": "clips",
    }
    assert (put.method, str(put.url), put.content) == (
        "PUT",
        "https://storage.example/put/up1",
        b"x" * 10,
    )
    assert "authorization" not in put.headers  # never leak the key to storage
    assert (put.headers["content-type"], put.headers["content-length"]) == ("video/mp4", "10")
    assert asset.id == ASSET_ID


def test_upload_presigned_skips_put_when_content_exists(make_client: MakeClient) -> None:
    rec = Recorder(envelope({"id": "up1", "alreadyExists": True}, 201), envelope(asset_payload()))
    make_client(rec).upload_presigned(b"abc", filename="a.png", content_hash="00ff")
    assert [r.method for r in rec.requests] == ["POST", "POST"]


def test_list_media_query_and_pagination(make_client: MakeClient) -> None:
    item = {"id": "a", "url": "u", "sizeBytes": "1"}
    rec = Recorder(
        envelope({"assets": [item, item], "pagination": {"page": 1, "limit": 2, "total": 3}}),
        envelope({"assets": [item], "pagination": {"page": 2, "limit": 2, "total": 3}}),
    )
    items = list(make_client(rec).list_all_media(limit=2, folder="avatars", recursive=True))
    assert len(items) == 3
    assert rec.requests[1].url.params["page"] == "2"
    assert dict(rec.requests[0].url.params) == {
        "folder": "avatars",
        "limit": "2",
        "page": "1",
        "recursive": "true",
    }


def test_list_all_media_stops_when_total_reached(make_client: MakeClient) -> None:
    item = {"id": "a", "url": "u"}
    rec = Recorder(envelope({"assets": [item], "pagination": {"total": 1}}))
    assert len(list(make_client(rec).list_all_media(limit=1))) == 1


def test_delete_returns_none_and_rejects_path_injection(make_client: MakeClient) -> None:
    rec = Recorder(envelope({"success": True}))
    client = make_client(rec)
    client.delete_media(ASSET_ID)
    assert (rec.last.method, rec.last.url.path) == ("DELETE", f"/api/v1/media/{ASSET_ID}")
    with pytest.raises(ValueError, match="Invalid id"):
        client.delete_media("../usage")


def test_folders_presets_usage(make_client: MakeClient) -> None:
    rec = Recorder(
        envelope({"id": "f1", "path": "2026/q1", "name": "q1"}),
        envelope({"folders": [], "currentFolder": None}),
        envelope({"id": "p1", "key": "thumb"}),
        envelope([{"id": "p1", "key": "thumb", "params": {"width": 200}}]),
        envelope({"storageBytes": "100", "imageCount": 1, "fileCount": 2, "folderCount": 3}),
    )
    client = make_client(rec)
    folder = client.create_folder(path="2026/q1", access_control_type="signed")
    client.list_folders(root_only=True)
    client.create_preset(key="thumb", name="Thumb", transform={"width": 200, "fit": "cover"})
    presets = client.list_presets()
    usage = client.get_usage()
    assert body_json(rec.requests[0]) == {"path": "2026/q1", "accessControlType": "signed"}
    assert rec.requests[1].url.params["parentId"] == "null"
    assert body_json(rec.requests[2]) == {
        "key": "thumb",
        "name": "Thumb",
        "width": 200,
        "fit": "cover",
    }
    assert (folder.id, presets[0].params, usage.storage_bytes) == ("f1", {"width": 200}, 100)


def test_processing_endpoints_unwrap_asset(make_client: MakeClient) -> None:
    cutout = {"id": "c", "url": "u", "format": "png"}
    rec = Recorder(
        envelope({"asset": cutout}),
        envelope({"asset": {**cutout, "status": "ready"}}, 201),
        envelope({"text": "INVOICE", "savedAsset": {"id": "t", "storageKey": "k"}}),
    )
    client = make_client(rec)
    assert client.remove_background(b"img", format="webp").format == "png"
    assert client.convert_document(b"doc", filename="a.docx", format="pdf").is_ready
    ocr = client.extract_text(b"img", folder="receipts", include_blocks=True)
    assert form_fields(rec.requests[0]) == {"format": "webp"}
    assert form_fields(rec.requests[2]) == {"folder": "receipts", "includeBlocks": "true"}
    assert (ocr.text, ocr.saved_asset and ocr.saved_asset.id) == ("INVOICE", "t")


def test_fetch_text_uses_public_url_without_key(make_client: MakeClient) -> None:
    rec = Recorder(httpx.Response(200, text="Total: $50"), httpx.Response(202))
    client = make_client(rec)
    asset = {"id": ASSET_ID, "url": f"{CDN_BASE}/{ASSET_ID}"}
    assert client.fetch_text(asset) == "Total: $50"
    assert str(rec.last.url) == f"{CDN_BASE}/{ASSET_ID}?format=txt"
    assert "authorization" not in rec.last.headers
    with pytest.raises(dreep.DreepProcessingError):
        client.fetch_text(asset, expires_in=60)
    assert "sig=" in str(rec.last.url)


def test_get_is_retried_on_503_then_succeeds(make_client: MakeClient) -> None:
    rec = Recorder(httpx.Response(503), httpx.Response(429), envelope({"storageBytes": 1}))
    assert make_client(rec).get_usage().storage_bytes == 1
    assert len(rec.requests) == 3


def test_get_gives_up_after_max_retries(make_client: MakeClient) -> None:
    rec = Recorder(httpx.Response(500), httpx.Response(500))
    with pytest.raises(dreep.DreepServerError):
        make_client(rec, max_retries=1).get_usage()
    assert len(rec.requests) == 2


def test_writes_are_never_retried(make_client: MakeClient) -> None:
    rec = Recorder(httpx.Response(503))
    with pytest.raises(dreep.DreepServerError):
        make_client(rec).upload(b"x")
    assert len(rec.requests) == 1


def test_connection_failures_map_to_typed_errors(make_client: MakeClient) -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    def slow(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(dreep.DreepConnectionError, match="refused"):
        make_client(Recorder(boom, boom, boom)).get_usage()
    with pytest.raises(dreep.DreepTimeoutError):
        make_client(Recorder(slow), max_retries=0).get_usage()


def test_typed_api_errors_surface(make_client: MakeClient) -> None:
    rec = Recorder(httpx.Response(402, json={"message": "out", "data": {"featureKey": "storage"}}))
    with pytest.raises(dreep.DreepLimitError) as info:
        make_client(rec).upload(b"x")
    assert info.value.feature_key == "storage"


def test_url_helpers_and_signing(make_client: MakeClient) -> None:
    client = make_client(Recorder())
    asset = dreep.Asset._from_api(asset_payload())
    assert client.url(asset, {"width": 400}).endswith(".webp?width=400")
    assert "&sig=" in client.signed_url(asset, expires_in=60)
    with pytest.raises(dreep.DreepError, match="signing secret"):
        make_client(Recorder(), signing_secret=None).signed_url(asset, expires_in=60)


def test_closing_leaves_injected_http_client_open() -> None:
    http = httpx.Client(transport=httpx.MockTransport(Recorder()))
    with Dreep(API_KEY, http_client=http):
        pass
    assert not http.is_closed
    http.close()
