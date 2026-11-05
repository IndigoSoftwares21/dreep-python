"""The async client, on both asyncio and trio, over representative paths.

Request building and parsing are shared with the sync client and covered in
test_client.py; these tests prove the generated pair stays behaviourally equal.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

import dreep
from tests.support import API_BASE, ASSET_ID, Recorder, asset_payload, envelope

pytestmark = pytest.mark.anyio

MakeClient = Callable[..., dreep.AsyncDreep]
ROOT = Path(__file__).resolve().parent.parent


async def test_upload_and_retry(make_async_client: MakeClient) -> None:
    rec = Recorder(envelope(asset_payload()), httpx.Response(503), envelope({"storageBytes": 5}))
    async with make_async_client(rec) as client:
        asset = await client.upload(b"bytes", filename="a.jpg")
        usage = await client.get_usage()
    assert (asset.id, usage.storage_bytes) == (ASSET_ID, 5)
    assert str(rec.requests[0].url) == f"{API_BASE}/upload"
    assert len(rec.requests) == 3


async def test_upload_presigned_streams_file(make_async_client: MakeClient, tmp_path: Path) -> None:
    path = tmp_path / "big.bin"
    path.write_bytes(b"y" * 2048)
    rec = Recorder(
        envelope({"id": "u", "uploadUrl": "https://storage.example/u"}, 201),
        httpx.Response(200),
        envelope(asset_payload()),
    )
    async with make_async_client(rec) as client:
        await client.upload_presigned(path, content_type="application/octet-stream")
    put = rec.requests[1]
    assert (put.content, put.headers["content-length"]) == (b"y" * 2048, "2048")
    assert "authorization" not in put.headers


async def test_list_all_media_is_an_async_iterator(make_async_client: MakeClient) -> None:
    rec = Recorder(envelope({"assets": [{"id": "a", "url": "u"}], "pagination": {"total": 1}}))
    async with make_async_client(rec) as client:
        items = [item async for item in client.list_all_media()]
    assert [i.id for i in items] == ["a"]


async def test_errors_are_typed(make_async_client: MakeClient) -> None:
    rec = Recorder(httpx.Response(404, json={"message": "gone"}))
    async with make_async_client(rec) as client:
        with pytest.raises(dreep.DreepNotFoundError, match="gone"):
            await client.delete_media("missing")


def test_generated_sync_client_is_up_to_date() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "unasync.py"), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
