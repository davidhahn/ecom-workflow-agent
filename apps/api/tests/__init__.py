# Registers every model module on Base.metadata before any test file runs,
# mirroring alembic/env.py's exact same need: a string-based ForeignKey
# (e.g. RequestLog.sql_query_audit_id -> "query_audit_log.id") only
# resolves against tables whose model class has actually been imported
# somewhere in the process. Without this, an isolated single-test-file run
# (any file that never happens to import audit_models/rag_models/
# observability_models through its own chain) fails on mapper configuration
# with NoReferencedTableError as soon as any ORM write touches Base's
# registry — not specific to which table you're writing to.
from app.db.models import Base  # noqa: F401
from app.db import audit_models  # noqa: F401 — registers QueryAuditLog on Base.metadata
from app.db import rag_models  # noqa: F401 — registers PolicyChunk on Base.metadata
from app.db import observability_models  # noqa: F401 — registers RequestLog on Base.metadata
