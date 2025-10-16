from unittest.mock import AsyncMock

import pytest

from app.bot.game.models import GameState
from app.store.bot import consts
from app.store.bot.gamebot.verdict_captain_state import VerdictCaptain
from app.store.tg_api.dataclasses import EntityTG


class TestVerdictCaptainState:
    @pytest.fixture
    def verdict_cap(self, mock_app):
        return VerdictCaptain(mock_app)

    @pytest.fixture
    def entity_mention(self, mock_app):
        return EntityTG(length=3, offset=123, type="mention")

    @pytest.mark.asyncio
    async def test_initialization(self, verdict_cap, mock_app):
        """Тест инициализации BotBase"""
        assert verdict_cap.app == mock_app
        assert verdict_cap.handlers is not None

        assert verdict_cap.game_store == verdict_cap.app.store.game_session

    @pytest.mark.asyncio
    async def test_handle_verdict_captain_other_text(
        self, verdict_cap, message, chat_id, entity_mention
    ):
        """Капитан выбирает игрока который будет отвечать.
        Капитан печатает что-то другое.
        """
        verdict_cap.add_message_in_unnecessary_messages = AsyncMock()
        await verdict_cap.handle_verdict_captain(
            message, GameState.VERDICT_CAPTAIN
        )
        verdict_cap.app.store.tg_api.send_message.assert_called_once_with(
            chat_id=chat_id, text=consts.CAPTAIN_INSTUCTION
        )
        verdict_cap.add_message_in_unnecessary_messages.assert_called()

    @pytest.mark.asyncio
    async def test_handle_verdict_captain_prints_not_cap(
        self, verdict_cap, message, chat_id, session_game, entity_mention
    ):
        """Капитан выбирает игрока который будет отвечать.
        Печатает не капитан или не вообще не игрок.
        """
        message.text = "@courvuisierr"
        entity_mention.offset = 1
        entity_mention.length = len(message.text[1:])
        message.entities = [
            entity_mention,
        ]

        verdict_cap.player_store.get_player_by_idtg = AsyncMock(
            return_value=None
        )
        verdict_cap.add_message_in_unnecessary_messages = AsyncMock()
        verdict_cap.game_store.get_active_session_by_chat_id = AsyncMock(
            return_value=session_game
        )
        await verdict_cap.handle_verdict_captain(
            message, GameState.VERDICT_CAPTAIN
        )
        verdict_cap.game_store.get_active_session_by_chat_id.assert_called_once_with(
            chat_id=session_game.chat_id,
        )
        verdict_cap.player_store.get_player_by_idtg.assert_called_once_with(
            session_id=session_game.id, id_tg=message.from_.id_
        )
        verdict_cap.app.store.tg_api.send_message.assert_called_once_with(
            chat_id=session_game.chat_id, text=consts.WARNING_CAPTAIN_ONLY
        )
        verdict_cap.add_message_in_unnecessary_messages.assert_called()

    @pytest.mark.asyncio
    async def test_handle_verdict_captain_chosen_player_dont_active(
        self,
        verdict_cap,
        message,
        chat_id,
        session_game,
        entity_mention,
        full_players,
        player1,
        player5,
    ):
        """Капитан выбирает игрока который будет отвечать.
        Выбранный игрок не активный, либо не готовый.
        """
        message.text = "@courvuisierr"
        entity_mention.offset = 1
        entity_mention.length = len(message.text[1:])
        message.entities = [
            entity_mention,
        ]
        session_game.players = full_players

        player5.is_active = False

        verdict_cap.player_store.get_player_by_username_tg = AsyncMock(
            return_value=player5
        )
        verdict_cap.player_store.get_player_by_idtg = AsyncMock(
            return_value=player1
        )
        verdict_cap.add_message_in_unnecessary_messages = AsyncMock()
        verdict_cap.game_store.get_active_session_by_chat_id = AsyncMock(
            return_value=session_game
        )
        await verdict_cap.handle_verdict_captain(
            message, GameState.VERDICT_CAPTAIN
        )
        verdict_cap.game_store.get_active_session_by_chat_id.assert_called_once_with(
            chat_id=session_game.chat_id,
        )
        verdict_cap.player_store.get_player_by_idtg.assert_called_once_with(
            session_id=session_game.id, id_tg=message.from_.id_
        )
        verdict_cap.app.store.tg_api.send_message.assert_called_once_with(
            chat_id=chat_id, text=consts.WARNING_CAP_DONT_EXIST_PLAYER
        )
        verdict_cap.add_message_in_unnecessary_messages.assert_called()

    @pytest.mark.asyncio
    async def test_handle_verdict_captain_chosen_player_is_active(
        self,
        verdict_cap,
        message,
        chat_id,
        session_game,
        entity_mention,
        full_players,
        player1,
        player5,
    ):
        """Капитан выбирает игрока который будет отвечать.
        Выбранный игрок не активный, либо не готовый.
        """
        message.text = "@courvuisierr"
        entity_mention.offset = 1
        entity_mention.length = len(message.text[1:])
        message.entities = [
            entity_mention,
        ]
        session_game.players = full_players

        player5.is_active = True
        player5.is_ready = True

        verdict_cap.player_store.get_player_by_username_tg = AsyncMock(
            return_value=player5
        )
        verdict_cap.player_store.get_player_by_idtg = AsyncMock(
            return_value=player1
        )
        verdict_cap.add_message_in_unnecessary_messages = AsyncMock()
        verdict_cap.game_store.get_active_session_by_chat_id = AsyncMock(
            return_value=session_game
        )
        verdict_cap.round_store.set_answer_player_id = AsyncMock()
        await verdict_cap.handle_verdict_captain(
            message, GameState.VERDICT_CAPTAIN
        )
        verdict_cap.game_store.get_active_session_by_chat_id.assert_called_once_with(
            chat_id=session_game.chat_id,
        )
        verdict_cap.player_store.get_player_by_idtg.assert_called_once_with(
            session_id=session_game.id, id_tg=message.from_.id_
        )
        verdict_cap.app.store.timer_manager.cancel_timer.assert_called_once_with(
            chat_id=session_game.chat_id, timer_type="2_minute_verdict_captain"
        )
        verdict_cap.round_store.set_answer_player_id.assert_called_once_with(
            session_id=session_game.id,
            answer_player_id=player5.id,
        )
        verdict_cap.app.store.fsm.set_state.assert_called_once_with(
            chat_id=session_game.chat_id, new_state=GameState.WAIT_ANSWER
        )
        verdict_cap.app.store.tg_api.send_message.assert_called_once_with(
            chat_id=session_game.chat_id,
            text=consts.PLAYER_QUESTION_INSTRUCTION.format(
                player=player5.user.username_tg
            ),
        )
        verdict_cap.add_message_in_unnecessary_messages.assert_called()
        verdict_cap.app.store.timer_manager.start_timer.assert_called_once_with(
            chat_id=session_game.chat_id,
            timeout=consts.WAIT_ANSWER_TIMEOUT,
            callback=verdict_cap.is_answer_false,
            timer_type="30_second_for_answer",
            # kwargs
            current_chat_id=session_game.chat_id,
            session_id=session_game.id,
            text="*Игрок долго не решался что ответить.* \n"
            "Вопрос засчитывается неверным.\n"
            "Готовы к следующему вопросу?",
        )
