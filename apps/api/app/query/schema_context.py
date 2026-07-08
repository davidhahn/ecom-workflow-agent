from app.db.models import Base
from app.query.constants import ALLOWED_TABLES, BLOCKED_COLUMNS


def build_schema_context() -> str:
    """Render the 6 Part 1 tables (name + column + type) for the system prompt.

    Derived from the SQLAlchemy models rather than hand-written so the prompt
    can't drift from the real schema. customers.email is deliberately omitted.
    """
    lines: list[str] = []
    for table in Base.metadata.sorted_tables:
        if table.name not in ALLOWED_TABLES:
            continue
        lines.append(f"{table.name} (")
        for column in table.columns:
            if (table.name, column.name) in BLOCKED_COLUMNS:
                continue
            nullability = "" if column.nullable else " NOT NULL"
            lines.append(f"  {column.name} {column.type}{nullability}")
        lines.append(")")
    return "\n".join(lines)
