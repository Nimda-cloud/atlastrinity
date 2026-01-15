"""
Database Connection Manager
"""

import asyncio
import os
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .schema import Base

# Default connection string (can be overridden by Env)
# Using 'postgresql+asyncpg' driver
DB_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://dev:postgres@localhost/atlastrinity_db")


class DatabaseManager:
    def __init__(self):
        self._engine = None
        self._session_maker = None
        self._semaphore = asyncio.Semaphore(15)  # Limit concurrent connections
        self.available = False

    async def initialize(self):
        """Initialize DB connection and create tables if missing."""
        try:
            self._engine = create_async_engine(
                DB_URL, 
                echo=False,
                pool_size=20,
                max_overflow=10,
                pool_pre_ping=True
            )

            # Create tables
            async with self._engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            self._session_maker = async_sessionmaker(self._engine, expire_on_commit=False)
            self.available = True
            print("[DB] Database initialized successfully.")
        except Exception as e:
            print(f"[DB] Failed to initialize database: {e}")
            self.available = False

    async def get_session(self) -> AsyncSession:
        """Get a new async session."""
        if not self.available or not self._session_maker:
            raise RuntimeError("Database not initialized")
        return self._session_maker()

    async def close(self):
        if self._engine:
            await self._engine.dispose()


db_manager = DatabaseManager()
