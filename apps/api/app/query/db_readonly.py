import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

load_dotenv()

# Query-path execution must go through the restricted ops_agent_readonly
# Postgres role (see alembic/versions for the role/grant migration), never the
# superuser/default connection used for migrations and seeding.
_base_url = make_url(
    os.environ["DATABASE_URL"].replace("postgresql://", "postgresql+psycopg://", 1)
)
READONLY_DATABASE_URL = _base_url.set(
    username="ops_agent_readonly",
    password=os.environ["OPS_AGENT_DB_PASSWORD"],
)

readonly_engine = create_engine(READONLY_DATABASE_URL, pool_pre_ping=True)
