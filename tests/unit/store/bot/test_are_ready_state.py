from unittest.mock import AsyncMock

import pytest

from app.bot.game.models import GameState
from app.store.bot import consts
from app.store.bot.gamebot.are_ready_state import AreReadyNextRoundPlayersProcessGameBot
from tests.unit.store.bot.conftest import session_game


class TestAreReadyState:
    @pytest.fixture
    def are_ready(self, mock_app):
        return AreReadyNextRoundPlayersProcessGameBot(mock_app)

    @pytest.mark.asyncio
    async def test_initialization(self, are_ready, mock_app):
        """Тест инициализации BotBase"""
        assert are_ready.app == mock_app
        assert are_ready.handlers is not None

        assert are_ready.game_store == are_ready.app.store.game_session


    @pytest.mark.asyncio
    async def test_handle_ready_dont_exist_session(
            self,
            are_ready,
            callback,
    ):
        """
        Тест на
        """
        callback.data = "ready"
        are_ready.game_store.get_active_session_by_chat_id = AsyncMock(
            return_value=None
        )
        await are_ready.handle_ready(
            callback, GameState.ARE_READY_NEXT_ROUND_PLAYERS
        )

        are_ready.app.store.tg_api.answer_callback_query.assert_called_once_with(
                callback_query_id=callback.id_,
                text=consts.DONT_EXIST_GAME_IN_CHAT,
        )

    @pytest.mark.asyncio
    async def test_handle_ready_if_user_not_participant(
            self,
            are_ready,
            callback,
            session_game,
            full_players,
            player7
    ):
        """
        Тест на
        """
        callback.data = "ready"
        callback.from_.username = player7.user.username_tg
        callback.from_.id_ = player7.user.id_tg

        session_game.players = full_players

        are_ready.game_store.get_active_session_by_chat_id = AsyncMock(
            return_value=session_game
        )
        await are_ready.handle_ready(
            callback, GameState.ARE_READY_NEXT_ROUND_PLAYERS
        )

        are_ready.app.store.tg_api.answer_callback_query.assert_called_once_with(
                callback_query_id=callback.id_,
                text=consts.YOU_DONT_PLAYER,
        )

    @pytest.mark.asyncio
    async def test_handle_ready_if_player_already_true(
            self,
            are_ready,
            callback,
            session_game,
            full_players,
            player6
    ):
        """
        Тест на
        """
        callback.data = "ready"
        callback.from_.username = player6.user.username_tg
        callback.from_.id_ = player6.user.id_tg

        session_game.players = full_players

        are_ready.game_store.get_active_session_by_chat_id = AsyncMock(
            return_value=session_game
        )
        await are_ready.handle_ready(
            callback, GameState.ARE_READY_NEXT_ROUND_PLAYERS
        )

        are_ready.app.store.tg_api.answer_callback_query.assert_called_once_with(
                callback_query_id=callback.id_,
                text=consts.ALREADY_CONFIRMED_READINESS,
        )

    @pytest.mark.asyncio
    async def test_handle_ready_player_make_ready(
            self,
            are_ready,
            callback,
            session_game,
            full_players,
            player5,
            player6
    ):
        """
        Тест на
        """
        callback.data = "ready"
        player5.is_ready = False
        player6.is_ready = False

        callback.from_.username = player6.user.username_tg
        callback.from_.id_ = player6.user.id_tg

        session_game.players = full_players

        are_ready.player_store.set_player_is_ready = AsyncMock()
        are_ready.game_store.get_active_session_by_chat_id = AsyncMock(
            return_value=session_game
        )
        await are_ready.handle_ready(
            callback, GameState.ARE_READY_NEXT_ROUND_PLAYERS
        )
        are_ready.player_store.set_player_is_ready.assert_called_once_with(
            session_id=session_game.id, id_tg=callback.from_.id_, new_active=True
        )
        are_ready.app.store.tg_api.answer_callback_query.assert_called_once_with(
            callback_query_id=callback.id_,
            text=consts.YOU_APPLY_READY,
        )

    @pytest.mark.asyncio
    async def test_handle_ready__make_ready_and_if_all_players_ready(
            self,
            are_ready,
            callback,
            session_game,
            full_players,
            player5,
            player6
    ):
        """
        Тест на
        """
        callback.data = "ready"
        player6.is_ready = False

        callback.from_.username = player6.user.username_tg
        callback.from_.id_ = player6.user.id_tg

        session_game.players = full_players

        are_ready.ask_question = AsyncMock()
        are_ready.game_store.get_active_session_by_chat_id = AsyncMock(
            return_value=session_game
        )
        await are_ready.handle_ready(
            callback, GameState.ARE_READY_NEXT_ROUND_PLAYERS
        )
        are_ready.player_store.set_player_is_ready.assert_called_once_with(
            session_id=session_game.id, id_tg=callback.from_.id_, new_active=True
        )
        are_ready.app.store.tg_api.answer_callback_query.assert_called_once_with(
            callback_query_id=callback.id_,
            text=consts.YOU_APPLY_READY,
        )
        are_ready.app.store.timer_manager.cancel_timer.assert_called_once_with(
            chat_id=callback.chat.id_, timer_type="30_second_are_ready"
        )
        are_ready.ask_question.assert_called_once_with(
            current_chat_id=callback.chat.id_, session_id=session_game.id
        )

