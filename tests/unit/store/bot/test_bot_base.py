from unittest.mock import AsyncMock

import pytest


class TestBotBase:
    """Тесты для базового класса BotBase"""

    @pytest.mark.asyncio
    async def test_initialization(self, bot_base, mock_app):
        """Тест инициализации BotBase"""
        assert bot_base.app == mock_app
        assert bot_base.handlers is not None

    @pytest.mark.asyncio
    async def test_add_message_in_unnecessary_messages(
        self, bot_base, mock_app
    ):
        """Тест добавления сообщения в список для удаления"""
        chat_id = 123
        message_id = 456

        # Настраиваем мок FSM
        mock_app.store.fsm.get_data.return_value = {}
        mock_app.store.fsm.update_data = AsyncMock()

        await bot_base.add_message_in_unnecessary_messages(chat_id, message_id)

        # Проверяем вызовы
        mock_app.store.fsm.get_data.assert_called_once_with(chat_id)
        mock_app.store.fsm.update_data.assert_called_once()
