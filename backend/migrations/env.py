import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection

from docs_qa.database import create_engine
from docs_qa.settings import get_settings

if context.config.config_file_name is not None:
    fileConfig(context.config.config_file_name)


def run_migrations(connection: Connection) -> None:
    context.configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_engine(get_settings().database.url)
    async with engine.connect() as connection:
        await connection.run_sync(run_migrations)
    await engine.dispose()


asyncio.run(run_async_migrations())
