"""Stream a large file to Dreep without holding it in memory.

DREEP_API_KEY=drp_live_... python examples/async_presigned_upload.py video.mp4
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from dreep import AsyncDreep


async def main(path: str) -> None:
    async with AsyncDreep() as client:
        asset = await client.upload_presigned(Path(path), folder="examples/large")
        sys.stdout.write(f"{asset.id} -> {asset.url}\n")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
