import os
import sys
import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


load_dotenv()

# Lazily create engine and sessionmaker so tests can configure DATABASE_URL
# and event loop policy before the engine is instantiated.
_engine = None
_AsyncSessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        DATABASE_URL = os.getenv("DATABASE_URL")
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL environment variable is required")
        # On Windows, ensure the selector event loop policy is set before
        # creating asyncpg connections. Some test runners or environments may
        # not have set this early enough which causes asyncpg connections to
        # be created on a different (closed) loop later.
        if sys.platform == "win32":
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            except Exception:
                pass

        engine_kwargs = {"pool_pre_ping": True}
        if os.getenv("PYTEST_CURRENT_TEST") or os.getenv("TEST_DATABASE_URL"):
            engine_kwargs["poolclass"] = NullPool

        _engine = create_async_engine(DATABASE_URL, **engine_kwargs)
    return _engine


def get_sessionmaker():
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        _AsyncSessionLocal = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _AsyncSessionLocal


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    Session = get_sessionmaker()
    async with Session() as session:
        yield session


__all__ = ["get_engine", "get_sessionmaker", "get_session"]


# Compatibility exports for existing code that imports `engine` and
# `AsyncSessionLocal` at module level. These are thin wrappers that
# lazily resolve to the real engine/sessionmaker so tests can control
# initialization timing.
class _LazyEngine:
    def __getattr__(self, name):
        return getattr(get_engine(), name)


def _async_session_local_factory():
    # Return a new AsyncSession instance (callable so existing code can
    # do `async with AsyncSessionLocal() as session:`)
    return get_sessionmaker()()


class AsyncSessionLocalProxy:
    """A proxy callable that returns AsyncSession instances.

    Tests can call `AsyncSessionLocal.set_factory(callable)` to install a
    custom factory (e.g., returning a transactional test session). The
    proxy object itself is import-stable so modules that did
    `from db.database import AsyncSessionLocal` keep working.
    """

    def __init__(self):
        self._factory = None

    def set_factory(self, fn):
        self._factory = fn

    def __call__(self):
        if self._factory is not None:
            return self._factory()
        return _async_session_local_factory()


engine = _LazyEngine()
AsyncSessionLocal = AsyncSessionLocalProxy()
__all__.extend(["engine", "AsyncSessionLocal"])
