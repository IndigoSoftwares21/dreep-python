# AGENTS.md — dreep-python

Rules for anyone (human or agent) changing this repository. The quality gate
enforces most of them; the rest are review standards.

## Core principle

> Client/transport communicates. Models describe. Domain logic decides.
> Constants define. Tests protect behaviour.

## Architecture

```
src/dreep/
  __init__.py              public API surface (the only re-export module)
  types.py                 public literals, Transform, re-exported models

  # pure layer: no I/O libraries (enforced by RULE-007)
  _constants.py            hosts, paths, headers, retry/timeout defaults
  _transform_constants.py  transform keys, server snapping tables
  _errors.py               exception hierarchy
  _error_mapping.py        HTTP status/body -> exception (the only place)
  _coerce.py, _decode.py   lenient JSON -> dataclass decoding
  _models.py, _models_project.py   response models (declarative)
  _jsnum.py                JavaScript-identical number/value rendering
  _transform.py            transform validation + canonical signing form
  _urls.py                 delivery and signed URLs
  _params.py               kwargs -> wire bodies/forms (camelCase derived)
  _files.py                file input normalisation, chunked reads
  _operations_*.py         one builder per endpoint: validate + describe

  # http layer
  _config.py, _http.py, _retry.py

  # client layer: the only code that sends requests or sleeps
  _async_core.py, _async_uploads.py, _async_media.py, _async_project.py, _async_client.py
  _sync_*.py, _client.py   GENERATED from the async files: never edit by hand
```

A request flows: public method → `op_*` builder (pure: validates, returns an
`Operation` = `Request` + parser) → `_run` (sends, retries GETs, maps errors)
→ parser → model.

## Hard rules

1. **Async is the source of truth.** Edit `_async_*.py`, then run
   `python scripts/unasync.py`. CI fails if the generated sync files are stale.
2. **No magic strings (RULE-004).** Behavioural literals live in the owning
   constants module. Wire field names are never spelled out: they are derived
   from Python names (`folder_id` → `folderId`) by `_params.wire_body` for
   requests and by `_decode` for responses. Exceptions need `wire(...)` metadata.
3. **DRY (RULE-005, RULE-006).** No six-line logic block twice; one definition
   per helper. Prefer the standard library (`http.HTTPStatus`) to re-declaring.
4. **Small modules (RULE-001).** Warn above 200 lines, fail above 400.
5. **Layering (RULE-007).** Pure modules never import `httpx`/`anyio`; only the
   client layer constructs an HTTP client.
6. **Writes are never retried.** Only GETs retry (429, 5xx, connection errors).
7. **Never send the API key anywhere but the API.** Absolute URLs (CDN fetches,
   presigned storage PUTs) go out without `Authorization`. Never log URLs that
   may be signed.
8. **Signing parity.** `_transform_constants` mirrors server tables. Changing
   breakpoints or canonical order without the server breaks every signed URL.
9. **Every suppression names its code (RULE-010).** `# type: ignore[code]`,
   `# noqa: CODE`, `# allow-magic: reason`.
10. **Tests ship with behaviour.** Bug fixes get a regression test. Coverage
    floor is 90%; flaky tests are defects.

## Workflow

- Setup: `bash scripts/setup_hooks.sh` (venv, deps, hooks).
- Gate: `bash scripts/quality_gate.sh` (runs on pre-commit and in CI).
- Branches: `<type>/<kebab-description>`; `main` is protected: open a PR.
- Commits: Conventional Commits, ≤100 characters per line, signed.
- Never bypass hooks with `--no-verify`.
- Rule debt only shrinks: `scripts/rules-baseline.json` fails on increases and
  on stale headroom. Update it with `--update-baseline` only when lowering it.
