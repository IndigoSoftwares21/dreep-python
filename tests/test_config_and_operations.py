"""Client configuration and the argument validation operations do before sending."""

from __future__ import annotations

import pytest

from dreep import NOT_GIVEN, DreepError
from dreep._config import ClientConfig, make_timeout, masked_key
from dreep._operations_media import op_convert_document, op_list_media, op_presign_upload
from dreep._operations_project import op_create_folder, op_create_preset, op_list_folders
from tests.support import API_KEY


def resolve(**overrides: object) -> ClientConfig:
    kwargs: dict[str, object] = {
        "api_key": API_KEY,
        "signing_secret": None,
        "timeout": 30.0,
        "max_retries": 2,
    }
    kwargs.update(overrides)
    return ClientConfig.resolve(**kwargs)  # type: ignore[arg-type]


def test_env_fallbacks_and_base_url_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DREEP_SIGNING_SECRET", "s")
    monkeypatch.setenv("DREEP_API_URL", "https://dev.local:8443/")
    config = resolve()
    assert (config.signing_secret, config.base_url) == ("s", "https://dev.local:8443")
    assert API_KEY not in repr(config)


@pytest.mark.parametrize(
    ("overrides", "error"),
    [
        ({"api_key": ""}, DreepError),
        ({"max_retries": -1}, ValueError),
        ({"timeout": 0}, ValueError),
    ],
)
def test_invalid_config_is_rejected(overrides: dict[str, object], error: type[Exception]) -> None:
    with pytest.raises(error):
        resolve(**overrides)


def test_masked_key_never_reveals_short_keys() -> None:
    assert masked_key("short") == "…"
    assert masked_key(API_KEY) == "drp_test_…cdef"


def test_connect_timeout_is_always_bounded() -> None:
    assert make_timeout(None).connect == 10.0
    assert make_timeout(None).read is None
    assert make_timeout(3).connect == 3
    assert repr(NOT_GIVEN) == "NOT_GIVEN"


@pytest.mark.parametrize(
    "call",
    [
        lambda: op_create_folder(
            name=None, path=None, parent_id=None, parent_path=None,
            access_control_type=None, default_expiry_seconds=None,
        ),
        lambda: op_create_folder(
            name=None, path="a/b", parent_id="p", parent_path=None,
            access_control_type=None, default_expiry_seconds=None,
        ),
        lambda: op_create_folder(
            name="a", path=None, parent_id="p", parent_path="q",
            access_control_type=None, default_expiry_seconds=None,
        ),
        lambda: op_list_folders(path="a", parent_id="b", root_only=False),
        lambda: op_list_media(page=None, limit=None, folder="a", folder_id="b", recursive=None),
        lambda: op_create_preset(key="", name="n", transform={"width": 1}),
        lambda: op_create_preset(key="has-hyphens", name="n", transform={"width": 1}),
        lambda: op_create_preset(key="Upper", name="n", transform={"width": 1}),
        lambda: op_create_folder(
            name=None, path="a/b", parent_id=None, parent_path=None,
            access_control_type="signed", default_expiry_seconds=None,
        ),
        lambda: op_create_folder(
            name="b", path=None, parent_id=None, parent_path="a",
            access_control_type="private", default_expiry_seconds=None,
        ),
        lambda: op_create_preset(key="k", name="n", transform={}),
        lambda: op_presign_upload(
            content_type="", size_bytes=1, filename=None, folder=None, key=None, folder_id=None,
            auto_create_folders=None, format=None, preset_key=None, content_hash=None,
        ),
        lambda: op_presign_upload(
            content_type="a/b", size_bytes=0, filename=None, folder=None, key=None, folder_id=None,
            auto_create_folders=None, format=None, preset_key=None, content_hash=None,
        ),
        lambda: op_convert_document(
            None, format="", page=None, key=None, folder=None, folder_id=None,  # type: ignore[arg-type]
            auto_create_folders=None,
        ),
    ],
)  # fmt: skip
def test_operations_reject_invalid_arguments_before_sending(call: object) -> None:
    with pytest.raises(ValueError, match=r"\w"):  # each case has its own message
        call()  # type: ignore[operator]


def test_root_folder_may_set_access_control() -> None:
    op = op_create_folder(
        name="premium", path=None, parent_id=None, parent_path=None,
        access_control_type="signed", default_expiry_seconds=600,
    )  # fmt: skip
    assert op.request.json == {
        "name": "premium",
        "accessControlType": "signed",
        "defaultExpirySeconds": 600,
    }
