#!/usr/bin/env python3
"""Print a database URL with URL-encoded credentials (safe for special chars in passwords)."""

from __future__ import annotations

import os
import sys
import urllib.parse


def build_url(*, async_driver: bool = True) -> str:
    user = os.environ.get("POSTGRES_USER", "arad")
    password = urllib.parse.quote(os.environ.get("POSTGRES_PASSWORD", "arad_pass"), safe="")
    db = os.environ.get("POSTGRES_DB", "arad_quality")
    host = os.environ.get("DB_HOST", "timescaledb")
    port = os.environ.get("DB_PORT", "5432")
    scheme = "postgresql+asyncpg" if async_driver else "postgresql"
    return f"{scheme}://{user}:{password}@{host}:{port}/{db}"


if __name__ == "__main__":
    use_async = "--sync" not in sys.argv
    print(build_url(async_driver=use_async))
