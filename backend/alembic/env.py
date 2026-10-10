from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, text

from alembic import context
from app.config import settings
from app.db import Base

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata

def run_migrations_offline():
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

# Arbitrary constant that identifies "GitTogether migrations" in Postgres' advisory-lock table.
MIGRATION_LOCK_ID = 727_374_001


def run_migrations_online():
    connectable = engine_from_config(config.get_section(config.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        # With 2+ backend replicas, several pods start at once and each runs `alembic upgrade head`.
        # A Postgres advisory lock makes them take turns: the first migrates, the rest wait and then
        # find nothing left to do. (SQLite, used by tests, has no such lock and doesn't need one.)
        postgres = connection.dialect.name == "postgresql"
        if postgres:
            connection.execute(text("SELECT pg_advisory_lock(:id)"), {"id": MIGRATION_LOCK_ID})
            connection.commit()
        try:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
        finally:
            if postgres:
                connection.execute(text("SELECT pg_advisory_unlock(:id)"), {"id": MIGRATION_LOCK_ID})
                connection.commit()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
