"""File input normalisation and request-parameter helpers."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from dreep._files import iter_chunks, open_file
from dreep._params import check_destination, check_exclusive, wire_body, wire_form


def test_bytes_input(tmp_path: Path) -> None:
    with open_file(b"abc") as f:
        assert (f.filename, f.content_type, f.size, f.stream.read()) == (
            "upload",
            "application/octet-stream",
            3,
            b"abc",
        )


def test_path_input_is_opened_and_closed(tmp_path: Path) -> None:
    path = tmp_path / "hero.png"
    path.write_bytes(b"\x89PNG")
    with open_file(path) as f:
        stream = f.stream
        assert (f.filename, f.content_type, f.size) == ("hero.png", "image/png", 4)
    assert stream.closed


def test_file_object_input_is_left_open_and_sized_from_position(tmp_path: Path) -> None:
    path = tmp_path / "doc.pdf"
    path.write_bytes(b"0123456789")
    with path.open("rb") as handle:
        handle.seek(4)
        with open_file(handle, filename="x.txt", content_type="text/x") as f:
            assert (f.filename, f.content_type, f.size) == ("x.txt", "text/x", 6)
        assert not handle.closed


def test_unseekable_stream_has_unknown_size() -> None:
    class Pipe(io.RawIOBase):
        def readable(self) -> bool:
            return True

    with open_file(Pipe()) as f:  # type: ignore[arg-type]
        assert f.size is None


@pytest.mark.parametrize("bad", ["hero.jpg", 42])
def test_rejects_str_and_unknown_types(bad: object) -> None:
    with pytest.raises(TypeError), open_file(bad):  # type: ignore[arg-type]
        pass


def test_iter_chunks_rejects_text_mode() -> None:
    with pytest.raises(TypeError, match="binary"):
        list(iter_chunks(io.StringIO("text"), 2))  # type: ignore[arg-type]
    assert list(iter_chunks(io.BytesIO(b"abcde"), 2)) == [b"ab", b"cd", b"e"]


def test_wire_body_camel_cases_and_drops_none() -> None:
    assert wire_body(folder_id="f", auto_create_folders=False, key=None) == {
        "folderId": "f",
        "autoCreateFolders": False,
    }
    assert wire_form(recursive=True, limit=20) == {"recursive": "true", "limit": "20"}


def test_check_exclusive() -> None:
    check_exclusive(a=1, b=None)
    with pytest.raises(ValueError, match="at most one of a, b"):
        check_exclusive(a=1, b=2)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"folder": "a", "key": "b", "folder_id": None},
        {"folder": "a", "key": None, "folder_id": "f"},
        {"folder": None, "key": "a/b.png", "folder_id": "f"},
    ],
)
def test_check_destination_rejects_ambiguity(kwargs: dict[str, str | None]) -> None:
    with pytest.raises(ValueError, match=r"folder|key"):
        check_destination(**kwargs)


def test_check_destination_allows_bare_key_with_folder_id() -> None:
    check_destination(folder=None, key="me.png", folder_id="f")
