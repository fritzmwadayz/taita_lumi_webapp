"""Async SQLAlchemy engine and session factory."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import AsyncAdaptedQueuePool

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.is_dev,  # SQL logging in dev
    pool_pre_ping=True,   # verify connection is alive before use
    # ── Pool settings — tuned for Neon free tier ──────────────
    # Neon free tier allows ~100 concurrent connections, but the
    # compute endpoint can suspend when idle. Small pool + recycling
    # keeps connections fresh without exhausting Neon's limit.
    poolclass=AsyncAdaptedQueuePool,
    pool_size=5,          # base connections kept open
    max_overflow=5,       # extra connections allowed under load
    pool_timeout=30,      # wait max 30s for a connection before giving up
    pool_recycle=1800,    # recycle connections every 30 minutes (Neon suspends after ~5min idle)
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields a DB session per request.

    The async with ensures the session (and its connection) is returned
    to the pool even if the request handler raises.
    """
    async with async_session() as session:
        yield session
