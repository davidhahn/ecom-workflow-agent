import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

load_dotenv()

# refund_evaluator's queries must go through the restricted
# refund_evaluator_readonly Postgres role (see alembic/versions for the
# role/grant migration), never the superuser/default connection used for
# migrations and seeding. Deliberately a separate role from
# ops_agent_readonly (app/query/db_readonly.py): that role excludes
# customers.email, but resolve_order_item() matches customers by email as
# well as name, so this role grants it - see the migration's docstring.
_base_url = make_url(
    os.environ["DATABASE_URL"].replace("postgresql://", "postgresql+psycopg://", 1)
)
REFUND_EVALUATOR_DATABASE_URL = _base_url.set(
    username="refund_evaluator_readonly",
    password=os.environ["REFUND_EVALUATOR_DB_PASSWORD"],
)

refund_evaluator_engine = create_engine(REFUND_EVALUATOR_DATABASE_URL, pool_pre_ping=True)
RefundEvaluatorSessionLocal = sessionmaker(
    bind=refund_evaluator_engine, autoflush=False, expire_on_commit=False
)
