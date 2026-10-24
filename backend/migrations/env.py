"""Apply migrations using environment configuration without printing credentials."""

from alembic import context
from app.db.models import Base
from app.db.repository import create_db_engine
from app.settings import Settings

target_metadata = Base.metadata


def run_migrations() -> None:
    """Run versioned schema changes in an explicit migration transaction."""
    if context.is_offline_mode():
        context.configure(
            url=Settings().database_url.get_secret_value(),
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
        )
        with context.begin_transaction():
            context.run_migrations()
        return
    engine = create_db_engine(Settings())
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


run_migrations()
