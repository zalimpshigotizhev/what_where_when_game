import asyncio
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.store.bot.gamebot import BotBase


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_app():
    """Создает мок объекта Application"""
    app = MagicMock()

    # Мок хранилища
    app.store = MagicMock()
    app.store.game_session = MagicMock()
    app.store.players = MagicMock()
    app.store.rounds = MagicMock()
    app.store.quizzes = MagicMock()
    app.store.fsm = MagicMock()
    app.store.tg_api = MagicMock()
    app.store.timer_manager = MagicMock()

    # Мок конфига
    app.config = MagicMock()
    app.config.bot = MagicMock()
    app.config.bot.token = "test_token"

    return app


# Фикстура для базового бота
@pytest.fixture
def bot_base(mock_app):
    """Создает экземпляр BotBase для тестирования"""
    return BotBase(mock_app)


# Фикстура для мока FSM контекста
@pytest.fixture
def mock_fsm_context():
    """Мок для FSMContext"""
    context = MagicMock()
    context.get_state = AsyncMock()
    context.set_state = AsyncMock()
    context.get_data = AsyncMock()
    context.update_data = AsyncMock()
    return context
