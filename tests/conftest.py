import logging
import os
from asyncio import AbstractEventLoop
from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from aiohttp.pytest_plugin import AiohttpClient
from aiohttp.test_utils import TestClient, loop_context
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from app.store import (
    Database,
    FSMContext,
    GameSessionAccessor,
    PlayerAccessor,
    RoundAccessor,
    Store,
    TimerManager,
)
from app.store.quiz.accessor import QuizAccessor
from app.store.tg_api.accessor import TelegramApiAccessor
from app.web.app import Application, setup_app
from app.web.config import Config


@pytest.fixture(scope="session")
def event_loop() -> Iterator[None]:
    with loop_context() as _loop:
        yield _loop


@pytest.fixture
def mock_app():
    """Создает Mock объекта Application"""
    app = MagicMock()
    # Мок хранилища
    app.store = MagicMock(spec=Store)
    app.store.players = MagicMock(spec=PlayerAccessor)
    app.store.rounds = MagicMock(spec=RoundAccessor)
    app.store.quizzes = MagicMock(spec=QuizAccessor)
    app.store.timer_manager = MagicMock(spec=TimerManager)
    app.store.game_session = MagicMock(spec=GameSessionAccessor)
    app.store.tg_api = MagicMock(spec=TelegramApiAccessor)
    app.store.fsm = MagicMock(spec=FSMContext)

    # Мок конфига
    app.config = MagicMock()
    app.config.bot = MagicMock()
    app.config.bot.token = "test_token"

    return app


@pytest.fixture(scope="session")
def app():
    """Создает объект Application"""
    app = setup_app(
        config_path=os.path.join(
            os.path.abspath(os.path.dirname(__file__)), "config.yaml"
        ),
        test_=True,
    )
    app.on_startup.clear()
    app.on_shutdown.clear()
    app.on_cleanup.clear()

    app.database = Database(app)

    app.on_startup.append(app.database.connect)
    app.on_startup.append(app.store.admins.connect)

    app.on_shutdown.append(app.database.disconnect)
    app.on_shutdown.append(app.store.admins.disconnect)
    return app


@pytest.fixture(autouse=True)
def cli(
    aiohttp_client: AiohttpClient,
    event_loop: AbstractEventLoop,
    app: Application,
) -> TestClient:
    return event_loop.run_until_complete(aiohttp_client(app))


@pytest.fixture
async def auth_cli(cli: TestClient, config: Config) -> TestClient:
    await cli.post(
        path="/admin.login",
        json={
            "email": config.admin.email,
            "password": config.admin.password,
        },
    )
    return cli


@pytest.fixture
def store(app):
    return app.store


@pytest.fixture
def db_sessionmaker(
    app: Application,
) -> async_sessionmaker[AsyncSession]:
    return app.database.session


@pytest.fixture
def db_engine(app: Application) -> AsyncEngine:
    return app.database.engine


@pytest.fixture
async def inspect_list_tables(db_engine: AsyncEngine) -> list[str]:
    def use_inspector(connection: AsyncConnection) -> list[str]:
        inspector = inspect(connection)
        return inspector.get_table_names()

    async with db_engine.begin() as conn:
        return await conn.run_sync(use_inspector)


@pytest.fixture(autouse=True)
async def clear_db(app: Application) -> Iterator[None]:
    try:
        yield
    except Exception as err:
        logging.warning(err)
    finally:
        session = AsyncSession(app.database.engine)
        connection = session.connection()
        for table in app.database._db.metadata.tables:
            await session.execute(text(f"TRUNCATE {table} CASCADE"))
            await session.execute(
                text(f"ALTER SEQUENCE {table}_id_seq RESTART WITH 1")
            )

        await session.commit()
        connection.close()


@pytest.fixture
def config(app: Application) -> Config:
    return app.config


@pytest.fixture
def id_tg():
    return 123


@pytest.fixture
def username_tg():
    return "courvuisier"


@pytest.fixture
def chat_id():
    return 1


@pytest.fixture
def session_id():
    return 1


@pytest.fixture
async def active_game_session(
    db_sessionmaker,
    session_id,
    chat_id,
):
    from app.bot.game.models import SessionModel, StatusSession

    async with db_sessionmaker() as sess:
        new_session = SessionModel(
            id=session_id,
            chat_id=chat_id,
            status=StatusSession.PROCESSING,
            current_round_id=None,
        )
        sess.add(new_session)
        await sess.commit()
    return new_session
