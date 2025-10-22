from typing import TYPE_CHECKING, Any

from attr import dataclass
from sqlalchemy import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.store.database.sqlalchemy_base import BaseModel

if TYPE_CHECKING:
    from app.web.app import Application


@dataclass
class DatabaseConfig:
    host: str = "localhost"
    port: int = 5432
    database: str = "demo"
    user: str | None = None
    password: str | None = None


class Database:
    def __init__(self, app: "Application") -> None:
        self.app = app

        self.engine: AsyncEngine | None = None
        self._db: type[DeclarativeBase] = BaseModel
        self.session: async_sessionmaker[AsyncSession] | None = None

    async def connect(self, *args: Any, **kwargs: Any) -> None:
        if self.engine:
            return
        db_config = self.app.config.database

        self.engine = create_async_engine(
            URL.create(
                drivername="postgresql+asyncpg",
                host=db_config.host,
                database=db_config.database,
                username=db_config.user,
                password=db_config.password,
                port=db_config.port,
            ),
            # echo=True,
        )
        self.session = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    async def disconnect(self, *args: Any, **kwargs: Any) -> None:
        if self.engine:
            await self.engine.dispose()

    async def get_session(self) -> AsyncSession:
        if not self.session:
            raise RuntimeError("Database is not connected")
        return self.session()
