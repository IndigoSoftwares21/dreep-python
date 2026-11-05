"""Delivery URL building and signed URL generation."""

from __future__ import annotations

import hashlib
import hmac
from datetime import timedelta

import pytest

from dreep import DreepError
from dreep._urls import build_signed_url, build_url
from tests.support import ASSET_ID, CDN_BASE, SIGNING_SECRET

ASSET = {"id": ASSET_ID, "url": f"{CDN_BASE}/{ASSET_ID}.webp"}
NOW = 1_774_000_000.9  # fractional on purpose: exp must floor it
EXP = 1_774_000_000 + 3600


def expected_sig(payload: str) -> str:
    return hmac.new(SIGNING_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()


def signed(transform: dict[str, object] | None = None) -> str:
    return build_signed_url(
        ASSET, signing_secret=SIGNING_SECRET, expires_in=3600, transform=transform, now=NOW
    )


def test_build_url_without_transform_returns_the_original() -> None:
    assert build_url(ASSET) == ASSET["url"]


def test_build_url_sorts_params_and_maps_preset() -> None:
    url = build_url(ASSET, {"width": 400, "format": "webp", "preset": "thumb"})
    assert url == f"{ASSET['url']}?format=webp&p=thumb&width=400"


def test_build_url_merges_existing_query_and_overrides_duplicates() -> None:
    url = build_url(f"{ASSET['url']}?width=10&zeta=1&width=20", {"width": 400})
    assert url == f"{ASSET['url']}?width=400&zeta=1"


def test_build_url_encodes_like_urlsearchparams() -> None:
    url = build_url("https://cdn.dreep.cloud/x", {"bg": "a b~c*d", "fit": "cover"})
    assert url.endswith("?bg=a+b%7Ec*d&fit=cover")


def test_build_url_accepts_objects_with_a_url_attribute() -> None:
    class Thing:
        url = ASSET["url"]

    assert build_url(Thing(), {"width": 1}) == f"{ASSET['url']}?width=1"


@pytest.mark.parametrize("target", [None, {}, "", "/relative/path", "ftp://cdn/x"])
def test_build_url_rejects_non_urls(target: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        build_url(target)


def test_signed_url_without_transform_signs_id_and_expiry() -> None:
    sig = expected_sig(f"{ASSET_ID}:{EXP}")
    assert signed() == f"{ASSET['url']}?exp={EXP}&sig={sig}"


@pytest.mark.parametrize(
    "transform",
    [
        {"width": 803, "format": "webp"},
        {"height": 500, "dpr": 1.5, "fit": "cover"},
        {"preset": "thumbnail"},
        {"crop": "1,2,3,4", "quality": 82},
    ],
)
def test_signature_covers_id_and_expiry_only(transform: dict[str, object]) -> None:
    """Matches the API reference and the live API: transforms are not signed."""
    url = signed(transform)
    assert url.endswith(f"&exp={EXP}&sig={expected_sig(f'{ASSET_ID}:{EXP}')}")
    assert url.startswith(build_url(ASSET, transform))


def test_transform_params_come_before_exp_and_sig() -> None:
    assert signed({"width": 803, "format": "webp"}).startswith(
        f"{ASSET['url']}?format=webp&width=803&exp="
    )


def test_signed_url_accepts_timedelta() -> None:
    url = build_signed_url(
        ASSET, signing_secret=SIGNING_SECRET, expires_in=timedelta(hours=1), now=NOW
    )
    assert f"exp={EXP}" in url


def test_signed_url_requires_a_secret() -> None:
    with pytest.raises(DreepError, match="signing secret"):
        build_signed_url(ASSET, signing_secret=None, expires_in=60)


@pytest.mark.parametrize("expires_in", [0, -5, 1.5, True, timedelta(seconds=1.5)])
def test_signed_url_rejects_bad_expiry(expires_in: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        build_signed_url(ASSET, signing_secret=SIGNING_SECRET, expires_in=expires_in)  # type: ignore[arg-type]


def test_signed_url_needs_the_asset_not_a_url() -> None:
    with pytest.raises(TypeError, match="asset itself"):
        build_signed_url(ASSET["url"], signing_secret=SIGNING_SECRET, expires_in=60)
