"""Motor y fábrica de sesiones hacia el único servidor PostgreSQL.

Todo el tráfico (lecturas de catálogo, carritos, pedidos y pagos) pasa por
este pool de conexiones: es el cuello de botella que el Sistema B elimina.
"""
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

_settings = get_settings()

engine: AsyncEngine = create_async_engine(
    _settings.database_url,
    pool_size=_settings.db_pool_size,
    max_overflow=_settings.db_max_overflow,
    pool_timeout=_settings.db_pool_timeout_s,
    pool_pre_ping=True,
)

SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Una sesión por petición HTTP; se cierra siempre al terminar."""
    async with SessionFactory() as session:
        yield session
