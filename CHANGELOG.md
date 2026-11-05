# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-11-05

### Fixed

- `signed_url()` now signs `"{id}:{exp}"` only, as the API reference specifies. 0.1.0
  also signed transform values, so signed links with most transforms or a preset were
  rejected with `401`. Verified against the live API.

### Added

- `create_preset()` rejects keys that aren't lowercase letters, numbers and underscores,
  with a clear message, before calling the API.
- `create_folder()` explains that access control can only be set on a top-level folder,
  instead of passing on the API's generic `400`.
- `Folder.default_expiry_seconds`.

### Removed

- Breakpoint rounding of signed transform values. The API doesn't sign transforms, so
  it was never needed.

## [0.1.0] - 2026-11-05

### Added

- `Dreep` (sync) and `AsyncDreep` (async, asyncio and trio) clients covering every
  endpoint: upload, presign, confirm, list, delete, folders, presets, usage, background
  removal, OCR and document conversion.
- `upload_presigned()`: presign, stream the PUT from disk, and confirm with retry.
- `url()` and `signed_url()`.
- `fetch_text()` for OCR on assets already stored in Dreep.
- Typed exception hierarchy, including `DreepLimitError` billing metadata.
- Retries for GET requests only, with exponential backoff and jitter, honouring
  `Retry-After`.

[Unreleased]: https://github.com/IndigoSoftwares21/dreep-python/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/IndigoSoftwares21/dreep-python/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/IndigoSoftwares21/dreep-python/releases/tag/v0.1.0
