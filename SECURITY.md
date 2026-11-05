# Security policy

## Reporting a vulnerability

**Please don't report security problems in public issues.** Use GitHub's
[private vulnerability reporting](https://github.com/IndigoSoftwares21/dreep-python/security/advisories/new)
instead. The maintainers, Abe Toluwani ([abetoluwani](https://github.com/abetoluwani)) and
Indigo ([IndigoSoftwares21](https://github.com/IndigoSoftwares21)), will acknowledge
your report, investigate it, and keep you updated until it is fixed.

Include the SDK version, a description of the problem and its impact, and how to
reproduce it. Never include real API keys or signing secrets.

## Supported versions

Security fixes are released for the latest minor version.

## How the SDK protects credentials

- The API key is sent only to the Dreep API. Presigned upload URLs and CDN fetch URLs
  are requested without it.
- Keys are masked in reprs, and URLs that may be signed are never logged.
- Only idempotent (GET) requests are retried, so no write is repeated without your knowledge.
