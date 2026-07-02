from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# Dynamically construct database connection parameters
engine_kwargs: dict[str, Any] = {
    "pool_pre_ping": True,  # Automatically verify connections before checking out
}

# Connection pooling limits do not apply to SQLite databases
if not settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update({
        "pool_size": 20,
        "max_overflow": 10,
    })

# Map standard connection strings to async equivalents for SQLAlchemy asyncpg/aiosqlite
database_url = settings.DATABASE_URL
connect_args: dict[str, Any] = {}

if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # Strip sync-only query params that cause asyncpg.connect() to crash
    if "sslmode" in database_url:
        import urllib.parse
        parsed = urllib.parse.urlparse(database_url)
        query_params = urllib.parse.parse_qs(parsed.query)

        sslmode = query_params.pop("sslmode", None)
        query_params.pop("channel_binding", None)  # Not supported by asyncpg

        new_query = urllib.parse.urlencode(query_params, doseq=True)
        parsed = parsed._replace(query=new_query)
        database_url = urllib.parse.urlunparse(parsed)

        # Configure SSL context for asyncpg connection
        if sslmode and sslmode[0] in ["require", "verify-ca", "verify-full"]:
            connect_args["ssl"] = True

elif database_url.startswith("sqlite:///"):
    database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)

engine = create_async_engine(database_url, connect_args=connect_args, **engine_kwargs)

async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency generator yielding async database sessions.
    Guarantees session cleanup upon route request completion.
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
