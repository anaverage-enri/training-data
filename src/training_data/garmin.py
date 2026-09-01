"""Authenticated Garmin Connect client, with retry handling."""

import time
from typing import Any, Callable

from garminconnect import Garmin

from training_data.config import RATE_LIMIT_SLEEP, TOKENSTORE


def client() -> Garmin:
    """Return a logged-in client using the cached OAuth token.

    No credentials needed — bin/login.py already wrote the token.
    Raises if the token is missing or rejected, which is what should be implemented:
    fail loudly rather than silently syncing nothing.
    """
    c = Garmin()
    c.login(str(TOKENSTORE))
    return c


def with_retry(fn: Callable[[], Any], attempts: int = 3, label: str = "") -> Any:
    """Call fn(), retrying with exponential backoff on failure.

    Garmin returns 429 (rate limited) and 403 (Cloudflare) fairly often.
    Backing off handles the transient cases; after `attempts` tries we give up
    and let the exception propagate so the run fails visibly rather than
    writing partial data.
    """
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            if i == attempts - 1:
                raise                           # last attempt: re-raise
            wait = RATE_LIMIT_SLEEP * (2 ** i)  # 1.5s, 3s, 6s
            print(f"  ! {label} failed ({e}); retrying in {wait:.1f}s")
            time.sleep(wait)

