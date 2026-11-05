"""Normalising the many shapes a file can arrive in.

Accepted inputs:

* ``bytes``, ``bytearray`` or ``memoryview`` -- content in memory.
* ``os.PathLike`` (e.g. :class:`pathlib.Path`) -- opened and closed by the SDK.
* A binary file object (anything with ``.read()`` returning bytes) -- read from
  its current position; the caller keeps ownership and closes it.

A plain ``str`` is rejected on purpose. It is ambiguous -- a path, or text
content? -- and guessing wrong would upload the literal string ``"hero.jpg"``.
Wrap paths in :class:`pathlib.Path`.
"""

from __future__ import annotations

import contextlib
import io
import mimetypes
import os
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Union

import anyio.to_thread

__all__ = ["FileInput", "PreparedFile", "aiter_chunks", "iter_chunks", "open_file"]

FileInput = Union[bytes, bytearray, memoryview, "os.PathLike[str]", IO[bytes]]

_FALLBACK_FILENAME = "upload"
_FALLBACK_CONTENT_TYPE = "application/octet-stream"


@dataclass
class PreparedFile:
    """A file ready to send: a binary stream plus its name, type and size."""

    stream: IO[bytes]
    filename: str
    content_type: str
    #: Bytes remaining from the stream's position, when it can be determined.
    size: int | None


def _guess_type(filename: str) -> str:
    guessed, _ = mimetypes.guess_type(filename, strict=False)
    return guessed or _FALLBACK_CONTENT_TYPE


def _remaining_size(stream: IO[bytes]) -> int | None:
    try:
        start = stream.tell()
        end = os.fstat(stream.fileno()).st_size
        return max(end - start, 0)
    except (AttributeError, OSError, io.UnsupportedOperation, ValueError):
        pass
    try:
        start = stream.tell()
        end = stream.seek(0, os.SEEK_END)
        stream.seek(start)
        return max(end - start, 0)
    except (AttributeError, OSError, io.UnsupportedOperation, ValueError):
        return None


@contextlib.contextmanager
def open_file(
    file: FileInput,
    *,
    filename: str | None = None,
    content_type: str | None = None,
) -> Iterator[PreparedFile]:
    """Yields a :class:`PreparedFile`, closing anything the SDK itself opened.

    The name resolves as: explicit ``filename``, else the path's or file
    object's own name, else ``"upload"``. The content type resolves as:
    explicit ``content_type``, else a guess from that name, else
    ``application/octet-stream``.
    """
    if isinstance(file, str):
        raise TypeError(
            "A str is ambiguous as a file. Pass pathlib.Path(...) for a path, "
            "or bytes for in-memory content."
        )

    owned: IO[bytes] | None = None
    try:
        if isinstance(file, (bytes, bytearray, memoryview)):
            data = bytes(file)
            stream: IO[bytes] = io.BytesIO(data)
            own_name: str | None = None
            size: int | None = len(data)
        elif isinstance(file, os.PathLike):
            path = Path(os.fspath(file))
            owned = stream = path.open("rb")
            own_name = path.name
            size = os.fstat(stream.fileno()).st_size
        elif callable(getattr(file, "read", None)):
            stream = file
            raw_name = getattr(file, "name", None)
            own_name = Path(raw_name).name if isinstance(raw_name, str) else None
            size = _remaining_size(stream)
        else:
            raise TypeError(
                f"Unsupported file type {type(file).__name__}. Pass bytes, a pathlib.Path, "
                "or a binary file object."
            )

        name = filename or own_name or _FALLBACK_FILENAME
        yield PreparedFile(
            stream=stream,
            filename=name,
            content_type=content_type or _guess_type(name),
            size=size,
        )
    finally:
        if owned is not None:
            owned.close()


_TEXT_MODE_MESSAGE = "File objects must be opened in binary mode ('rb')."


def _checked(chunk: object) -> bytes:
    if not isinstance(chunk, bytes):
        raise TypeError(_TEXT_MODE_MESSAGE)
    return chunk


def iter_chunks(stream: IO[bytes], chunk_size: int) -> Iterator[bytes]:
    """Reads a stream in fixed-size chunks, rejecting text-mode files early."""
    while chunk := _checked(stream.read(chunk_size)):
        yield chunk


async def aiter_chunks(stream: IO[bytes], chunk_size: int) -> AsyncIterator[bytes]:
    """:func:`iter_chunks` for async code: blocking reads run in a worker thread,
    so a slow disk never stalls the event loop."""
    while chunk := _checked(await anyio.to_thread.run_sync(stream.read, chunk_size)):
        yield chunk
