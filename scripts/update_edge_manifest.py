#!/usr/bin/env python3
"""Record the latest Cloudflare edge base URL for SIA v0.1."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from urllib.parse import urlparse

MANIFEST = Path("public/sia-edge.json")


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: update_edge_manifest.py <deployment-url>")

    url = sys.argv[1].strip().rstrip("/")
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise SystemExit("Cloudflare deployment URL must be an absolute HTTPS URL")

    data = {
        "version": "0.1",
        "cloudflare_base_url": url,
        "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"[SIA] Cloudflare edge recorded: {url}")


if __name__ == "__main__":
    main()
