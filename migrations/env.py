from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys
from pathlib import Path

# Cargar .env del backend para que Alembic use la misma DB que la app
backend_dir = Path(__file__).resolve().parent.parent
dotenv_path = backend_dir / ".env"
if dotenv_path.exists():
    from dotenv import load_dotenv
    load_dotenv(dotenv_path, override=True)

sys.path.insert(0, str(backend_dir))
from app.core.config import get_settings
from app.db.session import Base
from app.models import *

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata
# Preferir SQLite si está en .env del backend; si no, usar config por defecto
db_url = os.environ.get("DATABASE_URL") or get_settings().DATABASE_URL
if not db_url.startswith("sqlite"):
    db_url = f"sqlite:///{backend_dir / 'plan_accion.db'}"
config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
