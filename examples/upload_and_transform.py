"""Upload an image, then build delivery and signed URLs for it.

DREEP_API_KEY=drp_live_... DREEP_SIGNING_SECRET=... python examples/upload_and_transform.py hero.jpg
"""

from __future__ import annotations

import sys
from pathlib import Path

from dreep import Dreep, DreepError


def main(path: str) -> int:
    with Dreep() as client:
        try:
            asset = client.upload(Path(path), folder="examples", transform={"format": "webp"})
        except DreepError as error:
            sys.stderr.write(f"Upload failed: {error}\n")
            return 1
        sys.stdout.write(f"Stored:    {asset.url}\n")
        sys.stdout.write(f"Thumbnail: {client.url(asset, {'width': 200, 'fit': 'cover'})}\n")
        sys.stdout.write(f"Signed:    {client.signed_url(asset, expires_in=600)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
