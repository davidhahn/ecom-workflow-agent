"""In-memory draft store for the /tickets/draft -> /tickets/confirm flow.
Same single-process, dict-plus-lock shape as app/caching/cache.py, but
drafts are single-record lookups by draft_id (not a normalized-question
cache), and a confirmed draft is marked rather than deleted so a retried
confirm is idempotent instead of re-inserting or erroring.
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

DRAFT_TTL_SECONDS = 10 * 60

_lock = threading.Lock()
_store: dict[str, "DraftRecord"] = {}


@dataclass
class DraftRecord:
    fields: dict[str, Any]
    expires_at: float
    confirmed_ticket_id: uuid.UUID | None = field(default=None)


def create_draft(fields: dict[str, Any], ttl_seconds: float = DRAFT_TTL_SECONDS) -> str:
    draft_id = str(uuid.uuid4())
    with _lock:
        _store[draft_id] = DraftRecord(fields=fields, expires_at=time.monotonic() + ttl_seconds)
    return draft_id


def get_draft(draft_id: str) -> DraftRecord | None:
    with _lock:
        record = _store.get(draft_id)
        if record is None:
            return None
        if time.monotonic() > record.expires_at:
            del _store[draft_id]
            return None
        return record


def mark_confirmed(draft_id: str, ticket_id: uuid.UUID) -> None:
    with _lock:
        record = _store.get(draft_id)
        if record is not None:
            record.confirmed_ticket_id = ticket_id
