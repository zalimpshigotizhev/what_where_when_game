from unittest.mock import AsyncMock

import pytest

from app.bot.game.models import (
    GameState,
    StatusSession,
)
from app.store.bot import consts
from app.store.bot.gamebot.main_state import MainGameBot
from app.store.bot.keyboards import main_keyboard, start_game_keyboard
from app.store.rabbit.dataclasses import CommandTG


class TestMainGameBot:
    @pytest.fixture
    def main_bot(self, mock_app):
        """Создает мок объекта Application"""
        return MainGameBot(mock_app)

    @pytest.fixture
    def command(self, mock_app, chat_id):
        return CommandTG.from_dict(
            {
                "text": "/back",
                "chat": {
                    "id": chat_id,
                    "type": "group",
                    "title": "Во так вот",
                },
                "from": {
                    "first_name": "zalim",
                    "id": 12345,
                    "is_bot": False,
                    "is_premium": True,
                    "language_code": "ru",
                    "username": "courvuisier",
                },
            }
        )

    @pytest.fixture
    def command_back(self, command):
        """Создает command dataclass"""
        command.text = "/back"
        return command

    @pytest.fixture
    def command_start(self, command):
        """Создает command dataclass"""
        command.text = "/start"
        return command

    @pytest.mark.asyncio
    async def test_initialization(
        self,
        main_bot,
        mock_app,
    ):
        """Тест инициализации BotBase"""
        assert main_bot.app == mock_app
        assert main_bot.handlers is not None

        assert main_bot.game_store == mock_app.store.game_session

    @pytest.mark.asyncio
    async def test_handle_back_dont_exist_session(
        self, main_bot, mock_app, chat_id, command_back, session_game
    ):
        """Тест поведение /back если активной сессии не существует"""
        main_bot.game_store.get_active_session_by_chat_id = AsyncMock(
            return_value=None
        )

        await main_bot.handle_back(command_back, None)
        main_bot.app.store.tg_api.send_message.assert_called_once_with(
            chat_id=chat_id, text=consts.DONT_EXIST_GAME_IN_CHAT
        )

    @pytest.mark.asyncio
    async def test_handle_back_is_not_cap(
        self,
        main_bot,
        mock_app,
        chat_id,
        session_id,
        command_back,
        session_game,
        full_players,
        player2,
    ):
        """Тест поведение /back если отправил не капитан"""
        command_back.from_.id_ = player2.user.id_tg
        command_back.from_.username = player2.user.username_tg

        session_game.players = full_players
        main_bot.game_store.get_active_session_by_chat_id = AsyncMock(
            return_value=session_game
        )

        await main_bot.handle_back(command_back, None)
        main_bot.app.store.tg_api.send_message.assert_called_once_with(
            text=consts.CANCEL_GAME_ONLY_CAP,
            chat_id=chat_id,
        )

    @pytest.mark.asyncio
    async def test_handle_back_if_is_cap(
        self,
        main_bot,
        mock_app,
        chat_id,
        session_id,
        command_back,
        session_game,
        full_players,
        player1,
    ):
        """Тест поведение /back если отправил капитан"""
        command_back.from_.id_ = player1.user.id_tg
        command_back.from_.username = player1.user.username_tg
        session_game.players = full_players
        game_store = main_bot.game_store
        game_store.get_active_session_by_chat_id = AsyncMock(
            return_value=session_game
        )
        main_bot.cancel_game = AsyncMock()
        await main_bot.handle_back(command_back, None)
        main_bot.cancel_game.assert_called_once_with(
            current_chat_id=chat_id, session_id=session_id
        )

    @pytest.mark.asyncio
    async def test_handle_start_command_status_processing(
        self,
        main_bot,
        mock_app,
        chat_id,
        session_id,
        command_start,
        session_game,
    ):
        """Тест поведение /start, но сессия со статусом PROCCESSING уже есть"""
        session_game.status = StatusSession.PROCESSING
        game_store = main_bot.game_store
        game_store.get_active_session_by_chat_id.return_value = session_game
        main_bot.add_message_in_unnecessary_messages = AsyncMock()

        await main_bot.handle_start_command(command_start, None)
        main_bot.app.store.tg_api.send_message.assert_called_once_with(
            chat_id=chat_id, text=consts.EXIST_GAME_CAN_EXIT, reply_markup=None
        )
        main_bot.add_message_in_unnecessary_messages.assert_called()

    @pytest.mark.asyncio
    async def test_handle_start_command_status_pending(
        self,
        main_bot,
        mock_app,
        chat_id,
        session_id,
        command_start,
        session_game,
    ):
        """Тест поведение /start, но сессия со статусом PENDING уже есть"""
        game_store = main_bot.game_store
        session_game.status = StatusSession.PENDING
        game_store.get_active_session_by_chat_id.return_value = session_game
        main_bot.add_message_in_unnecessary_messages = AsyncMock()
        game_store.create_session = AsyncMock()

        await main_bot.handle_start_command(command_start, None)
        game_store.create_session.assert_not_called()
        main_bot.app.store.tg_api.send_message.assert_called_once_with(
            chat_id=chat_id,
            text=consts.WELCOME_TO_GAME,
            reply_markup=main_keyboard,
        )
        main_bot.add_message_in_unnecessary_messages.assert_called()

    async def test_handle_start_command_dont_exist_session(
        self,
        main_bot,
        mock_app,
        chat_id,
        session_id,
        command_start,
        session_game,
    ):
        """Тест поведение /start, но активной сессии не существует"""
        main_bot.game_store.get_active_session_by_chat_id.return_value = None
        main_bot.add_message_in_unnecessary_messages = AsyncMock()
        main_bot.game_store.create_session = AsyncMock()

        await main_bot.handle_start_command(command_start, None)
        main_bot.game_store.create_session.assert_called_once_with(
            chat_id=chat_id,
            status=StatusSession.PENDING,
        )
        main_bot.app.store.tg_api.send_message.assert_called_once_with(
            chat_id=chat_id,
            text=consts.WELCOME_TO_GAME,
            reply_markup=main_keyboard,
        )
        main_bot.add_message_in_unnecessary_messages.assert_called()

    @pytest.mark.asyncio
    async def test_handle_start_game_dont_exist_session(
        self, main_bot, mock_app, chat_id, session_id, session_game, callback
    ):
        """Тест поведение если нажимается кнопка,
        а игры не существует в этом чате
        """
        main_bot.game_store.get_active_session_by_chat_id.return_value = None

        await main_bot.handle_start_game(callback, None)

        main_bot.app.store.tg_api.answer_callback_query.assert_called_once_with(
            callback_query_id=callback.id_, text=consts.THIS_GAME_COMPLETED
        )

    @pytest.mark.asyncio
    async def test_handle_start_game_is_exist_session(
        self, main_bot, mock_app, chat_id, session_id, session_game, callback
    ):
        """Тест поведение если нажимается кнопка, а игра уже идет в этом чате"""
        session_game.status = StatusSession.PROCESSING
        game_store = main_bot.game_store
        game_store.get_active_session_by_chat_id.return_value = session_game

        await main_bot.handle_start_game(callback, None)

        main_bot.app.store.tg_api.answer_callback_query.assert_called_once_with(
            callback_query_id=callback.id_, text=consts.GAME_IS_EXIST
        )

    @pytest.mark.asyncio
    async def test_handle_start_game(
        self, main_bot, mock_app, chat_id, session_id, session_game, callback
    ):
        """Тест поведение начинается игра"""
        game_store = main_bot.game_store
        main_bot.deleted_unnecessary_messages = AsyncMock()
        game_store.set_status = AsyncMock()
        main_bot.add_message_in_unnecessary_messages = AsyncMock()
        session_game.status = StatusSession.PENDING
        game_store.get_active_session_by_chat_id.return_value = session_game

        await main_bot.handle_start_game(callback, None)

        main_bot.player_store.create_player.assert_called_once_with(
            session_id=session_game.id,
            id_tg=callback.from_.id_,
            username_tg=callback.from_.username,
            is_captain=True,
        )
        main_bot.deleted_unnecessary_messages.assert_called_once_with(
            chat_id=chat_id
        )
        main_bot.app.store.tg_api.answer_callback_query.assert_called_once_with(
            callback_query_id=callback.id_,
            text=consts.ALERT_FOR_CAP,
        )
        main_bot.app.store.tg_api.send_message.assert_called_once_with(
            chat_id=chat_id,
            text=consts.INFORMATION_ABOUT_CAP.format(
                username=callback.from_.username
            ),
            reply_markup=start_game_keyboard,
        )
        main_bot.game_store.set_status.assert_called_once_with(
            session_id=session_id, new_status=StatusSession.PROCESSING
        )
        main_bot.app.store.fsm.set_state.assert_called_once_with(
            chat_id=chat_id, new_state=GameState.WAITING_FOR_PLAYERS
        )
        main_bot.add_message_in_unnecessary_messages.assert_called()

    @pytest.mark.asyncio
    async def test_handle_show_rules(
        self, main_bot, mock_app, chat_id, session_id, callback, session_game
    ):
        """Тест поведение /back если отправил капитан"""
        main_bot.add_message_in_unnecessary_messages = AsyncMock()
        callback.data = "show_rules"

        await main_bot.handle_show_rules(callback, None)
        main_bot.app.store.tg_api.send_message.assert_called_once_with(
            chat_id=callback.chat.id_, text=consts.RULES_INFO
        )
        main_bot.add_message_in_unnecessary_messages.assert_called()

    @pytest.mark.asyncio
    async def test_handle_show_rating(
        self, main_bot, mock_app, chat_id, callback, session_game
    ):
        """Тест поведение /back если отправил капитан"""
        main_bot.add_message_in_unnecessary_messages = AsyncMock()
        experts = 1
        bot = 2
        completed_sessions = [
            session_game,
        ]
        main_bot.game_store.gen_score = AsyncMock(
            return_value={
                "experts": experts,
                "bot": bot,
                "total_rounds": 3,
            }
        )
        main_bot.game_store.get_completed_sessions = AsyncMock(
            return_value=completed_sessions
        )

        callback.data = "show_rating"

        await main_bot.handle_show_rating(callback, None)
        main_bot.game_store.get_completed_sessions.assert_called_once_with(
            chat_id=callback.chat.id_
        )
        main_bot.game_store.gen_score.assert_called_once_with(
            session_id=session_game.id
        )

        main_bot.app.store.tg_api.send_message.assert_called_once_with(
            callback.chat.id_,
            consts.RATING_INFO.format(
                count=len(completed_sessions),
                experts=experts,
                bot=bot,
            ),
        )
        main_bot.add_message_in_unnecessary_messages.assert_called()
