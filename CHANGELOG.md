# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-11-05

### Added

- `Dreep` (sync) and `AsyncDreep` (async, asyncio and trio) clients covering every
  endpoint: upload, presign, confirm, list, delete, folders, presets, usage, background
  removal, OCR and document conversion.
- `upload_presigned()`: presign, stream the PUT from disk, and confirm with retry.
- `url()` and `signed_url()`, matching the API's breakpoint snapping and canonical
  signing payload.
- `fetch_text()` for OCR on assets already stored in Dreep.
- Typed exception hierarchy, including `DreepLimitError` billing metadata.
- Retries for GET requests only, with exponential backoff and jitter, honouring
  `Retry-After`.
