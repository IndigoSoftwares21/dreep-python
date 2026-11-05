"""Test helpers: canned payloads, a recording transport, request decoders."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx

API_KEY = "drp_test_0123456789abcdef"
SIGNING_SECRET = "test_signing_secret"
API_BASE = "https://api.dreep.cloud/api/v1"
CDN_BASE = "https://cdn.dreep.cloud/api/v1/fetch"
ASSET_ID = "2f928a3f-1d2a-4a2b-8a8b-123456789abc"

Handler = Callable[[httpx.Request], httpx.Response]


def envelope(data: Any, status: int = 200) -> httpx.Response:
    """A success response wrapped the way the API wraps them."""
    return httpx.Response(status, json={"message": "ok", "code": "OK", "data": data})


def asset_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "id": ASSET_ID,
        "url": f"{CDN_BASE}/{ASSET_ID}.webp",
        "originalFilename": "hero.jpg",
        "mimetype": "image/webp",
        "format": "webp",
        "sizeBytes": "245000",
        "width": 1200,
        "height": 800,
        "status": "ready",
        "folder": "marketing/2026",
        "folderId": "78b52933-5541-4e90-8c15-39a84a412da8",
        "projectId": "3ca76fa8-0000-0000-0000-000000000000",
        "createdAt": "2026-08-16T18:53:29.000Z",
    }
    payload.update(overrides)
    return payload


def body_json(request: httpx.Request) -> Any:
    return json.loads(request.content)


def form_fields(request: httpx.Request) -> dict[str, str]:
    """The non-file fields of a multipart request, parsed crudely but sufficiently."""
    content_type = request.headers["content-type"]
    boundary = content_type.split("boundary=")[1].encode()
    fields = {}
    for part in request.read().split(b"--" + boundary):
        head, _, value = part.partition(b"\r\n\r\n")
        if b'name="' in head and b"filename=" not in head:
            name = head.split(b'name="')[1].split(b'"')[0].decode()
            fields[name] = value.rstrip(b"\r\n").decode()
    return fields


class Recorder:
    """A handler that records requests and answers from a scripted queue."""

    def __init__(self, *responses: httpx.Response | Handler) -> None:
        self.responses = list(responses)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        request.read()
        self.requests.append(request)
        if not self.responses:
            raise AssertionError(f"Unexpected request: {request.method} {request.url}")
        response = self.responses.pop(0)
        return response(request) if callable(response) else response

    @property
    def last(self) -> httpx.Request:
        return self.requests[-1]
