"""In-memory TTL cache for the read/analysis endpoints (/query/analyze,
/query/sql, /query/rag). Not Redis — a single-process dict is fine for now,
per the scope of this pass.

Routes are sync (`def`, not `async def`) and run in FastAPI's shared
threadpool, so gets/sets need a lock rather than assuming single-threaded
access.

Keyed by (namespace, normalized_key) — namespaced per endpoint so the same
question text asked to /query/analyze vs /query/sql doesn't collide, since
they mean different things there.
"""

import threading
import time
from typing import Any

CACHE_TTL_SECONDS = 4 * 60 * 60

_lock = threading.Lock()
_store: dict[tuple[str, str], tuple[Any, float]] = {}


def normalize_key(text: str) -> str:
    return text.strip().lower()


def cache_get(namespace: str, key: str) -> Any | None:
    entry_key = (namespace, key)
    with _lock:
        entry = _store.get(entry_key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del _store[entry_key]
            return None
        return value


def cache_set(namespace: str, key: str, value: Any, ttl_seconds: float = CACHE_TTL_SECONDS) -> None:
    with _lock:
        _store[(namespace, key)] = (value, time.monotonic() + ttl_seconds)
