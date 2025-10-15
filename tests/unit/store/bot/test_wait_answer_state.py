import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from app.bot.game.models import RoundModel, GameState
from app.quiz.models import QuestionModel, AnswerModel, ThemeModel
from app.store.bot import consts
from app.store.bot.gamebot.wait_answer_state import WaitAnswer
from tests.unit.store.bot.conftest import chat_id


class TestWaitAnswer:
    @pytest.fixture
    def wait_answer(self, mock_app):
        return WaitAnswer(mock_app)

    @pytest.fixture
    def correct_round(self, session_game, player5):
        return RoundModel(
            id=1,
            session_id=session_game.id,
            is_active=True,
            is_correct_answer=None,
            answer_player=player5,
            question=QuestionModel(
                id=1,
                title="Аисты кидают туда ребенка, назовите овощ?",
                theme=ThemeModel(
                    id=1,
                    title="Дети"
                ),
                true_answer=AnswerModel(
                    id=1,
                    title="Капуста",
                    description="Детям ведь, не скажешь правду"
                )
            )
        )

    @pytest.mark.asyncio
    async def test_initialization(self, wait_answer, mock_app):
        """Тест инициализации BotBase"""
        assert wait_answer.app == mock_app
        assert wait_answer.handlers is not None

        assert wait_answer.game_store == wait_answer.app.store.game_session

    @pytest.mark.asyncio
    async def test_handle_wait_answer_wrong_player_answered(
            self,
            wait_answer,
            message,
            session_game,
            chat_id,
            full_players,
            player4,
            correct_round
    ):
        """
        Тест если отвечает не выбранный капитаном игрок.
        """
        message.from_.username = player4.user.username_tg
        message.from_.id_ = player4.user.id_tg

        session_game.current_round = correct_round
        wait_answer.is_answer_false = AsyncMock()
        wait_answer.game_store.get_active_session_by_chat_id = AsyncMock(
            return_value=session_game
        )

        await wait_answer.handle_wait_answer(
            message, GameState.WAIT_ANSWER
        )
        wait_answer.game_store.get_active_session_by_chat_id.assert_called_with(
            chat_id=session_game.chat_id
        )

        wait_answer.is_answer_false.assert_called_once_with(
            session_id=session_game.id,
            current_chat_id=chat_id,
            text=f"Должен был ответить - @{session_game.current_round.answer_player.user.username_tg}\n"
                 f"А ответил @{message.from_.username}\n"
                 f"*Ответ засчитан как неправильный! Будьте внимательны*",
        )


    @pytest.mark.asyncio
    async def test_handle_wait_answer_false_game_continue(
            self,
            wait_answer,
            message,
            session_game,
            chat_id,
            full_players,
            player5,
            correct_round
    ):
        """
        Тест если ответ неправильный. Игра продолжается
        """
        message.text = "Корова"
        message.from_.username = player5.user.username_tg
        message.from_.id_ = player5.user.id_tg

        session_game.current_round = correct_round

        session_game.current_round.question.is_answer_is_true = Mock(
            return_value=False
        )
        escape_markdown = Mock()
        wait_answer.round_store.set_is_correct_answer = AsyncMock()
        wait_answer.round_store.set_is_active_to_false = AsyncMock()
        wait_answer.next_quest = AsyncMock()
        wait_answer.check_and_notify_score = AsyncMock(
            return_value=True
        )

        wait_answer.is_answer_false = AsyncMock()
        wait_answer.game_store.get_active_session_by_chat_id = AsyncMock(
            return_value=session_game
        )

        await wait_answer.handle_wait_answer(
            message, GameState.WAIT_ANSWER
        )
        wait_answer.game_store.get_active_session_by_chat_id.assert_called_with(
            chat_id=session_game.chat_id
        )
        wait_answer.app.store.timer_manager.cancel_timer.assert_called_with(
            chat_id=chat_id, timer_type="30_second_for_answer"
        )

        session_game.current_round.question.is_answer_is_true(message.text)
        wait_answer.app.store.tg_api.send_message.assert_called_with(
            chat_id=chat_id,
            text=consts.IS_ANSWER_FALSE.format(
                answer=session_game.current_round.question.true_answer.title
            ),
        )
        wait_answer.round_store.set_is_correct_answer.assert_called_once_with(
            session_id=session_game.id, new_is_correct_answer=False
        )
        wait_answer.round_store.set_is_active_to_false.assert_called_once_with(
            session_id=session_game.id
        )
        wait_answer.check_and_notify_score.assert_called_once_with(
            session_id=session_game.id, chat_id=chat_id
        )
        wait_answer.next_quest.assert_called_once_with(
            text=consts.ARE_YOU_READY_NEXT_QUEST,
            chat_id=chat_id,
            session_id=session_game.id,
        )

    @pytest.mark.asyncio
    async def test_handle_wait_answer_not_false_game_stop(
            self,
            wait_answer,
            message,
            session_game,
            chat_id,
            full_players,
            player5,
            correct_round
    ):
        """
        Тест если ответ неправильный. Игра заканчивается
        """
        message.text = "Корова"
        message.from_.username = player5.user.username_tg
        message.from_.id_ = player5.user.id_tg

        session_game.current_round = correct_round

        session_game.current_round.question.is_answer_is_true = Mock(
            return_value=False
        )
        escape_markdown = Mock()
        wait_answer.round_store.set_is_correct_answer = AsyncMock()
        wait_answer.round_store.set_is_active_to_false = AsyncMock()
        wait_answer.next_quest = AsyncMock()
        wait_answer.check_and_notify_score = AsyncMock(
            return_value=False
        )

        wait_answer.is_answer_false = AsyncMock()
        wait_answer.game_store.get_active_session_by_chat_id = AsyncMock(
            return_value=session_game
        )

        await wait_answer.handle_wait_answer(
            message, GameState.WAIT_ANSWER
        )
        wait_answer.game_store.get_active_session_by_chat_id.assert_called_with(
            chat_id=session_game.chat_id
        )
        wait_answer.app.store.timer_manager.cancel_timer.assert_called_with(
            chat_id=chat_id, timer_type="30_second_for_answer"
        )

        session_game.current_round.question.is_answer_is_true(message.text)
        wait_answer.app.store.tg_api.send_message.assert_called_with(
            chat_id=chat_id,
            text=consts.IS_ANSWER_FALSE.format(
                answer=session_game.current_round.question.true_answer.title
            ),
        )
        wait_answer.round_store.set_is_correct_answer.assert_called_once_with(
            session_id=session_game.id, new_is_correct_answer=False
        )
        wait_answer.round_store.set_is_active_to_false.assert_called_once_with(
            session_id=session_game.id
        )
        wait_answer.check_and_notify_score.assert_called_once_with(
            session_id=session_game.id, chat_id=chat_id
        )
        wait_answer.next_quest.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_wait_answer_true_game_continue(
            self,
            wait_answer,
            message,
            session_game,
            chat_id,
            full_players,
            player5,
            correct_round
    ):
        """
        Тест если ответ неправильный. Игра заканчивается
        """
        message.text = "Корова"
        message.from_.username = player5.user.username_tg
        message.from_.id_ = player5.user.id_tg

        session_game.current_round = correct_round

        session_game.current_round.question.is_answer_is_true = Mock(
            return_value=True
        )
        escape_markdown = Mock()
        asyncio.sleep = AsyncMock()
        wait_answer.round_store.set_is_correct_answer = AsyncMock()
        wait_answer.round_store.set_is_active_to_false = AsyncMock()
        wait_answer.next_quest = AsyncMock()
        wait_answer.check_and_notify_score = AsyncMock(
            return_value=True
        )

        wait_answer.is_answer_false = AsyncMock()
        wait_answer.game_store.get_active_session_by_chat_id = AsyncMock(
            return_value=session_game
        )

        await wait_answer.handle_wait_answer(
            message, GameState.WAIT_ANSWER
        )
        wait_answer.game_store.get_active_session_by_chat_id.assert_called_with(
            chat_id=session_game.chat_id
        )
        wait_answer.app.store.timer_manager.cancel_timer.assert_called_with(
            chat_id=chat_id, timer_type="30_second_for_answer"
        )

        session_game.current_round.question.is_answer_is_true(message.text)
        wait_answer.app.store.tg_api.send_message.assert_called_with(
            chat_id=chat_id,
            text=consts.IS_ANSWER_TRUE.format(
                answer=session_game.current_round.question.true_answer.title
            ),
        )
        wait_answer.round_store.set_is_correct_answer.assert_called_once_with(
            session_id=session_game.id, new_is_correct_answer=True
        )
        wait_answer.round_store.set_is_active_to_false.assert_called_once_with(
            session_id=session_game.id
        )
        wait_answer.check_and_notify_score.assert_called_once_with(
            session_id=session_game.id, chat_id=chat_id
        )
        wait_answer.next_quest.assert_called_once_with(
            text=consts.ARE_YOU_READY_NEXT_QUEST,
            chat_id=chat_id,
            session_id=session_game.id,
        )

    @pytest.mark.asyncio
    async def test_handle_wait_answer_true_game_stop(
            self,
            wait_answer,
            message,
            session_game,
            chat_id,
            full_players,
            player5,
            correct_round
    ):
        """
        Тест если ответ неправильный. Игра заканчивается
        """
        message.text = "Корова"
        message.from_.username = player5.user.username_tg
        message.from_.id_ = player5.user.id_tg

        session_game.current_round = correct_round
        asyncio.sleep = AsyncMock()

        session_game.current_round.question.is_answer_is_true = Mock(
            return_value=True
        )
        escape_markdown = Mock()
        wait_answer.round_store.set_is_correct_answer = AsyncMock()
        wait_answer.round_store.set_is_active_to_false = AsyncMock()
        wait_answer.next_quest = AsyncMock()
        wait_answer.check_and_notify_score = AsyncMock(
            return_value=False
        )

        wait_answer.is_answer_false = AsyncMock()
        wait_answer.game_store.get_active_session_by_chat_id = AsyncMock(
            return_value=session_game
        )

        await wait_answer.handle_wait_answer(
            message, GameState.WAIT_ANSWER
        )
        wait_answer.game_store.get_active_session_by_chat_id.assert_called_with(
            chat_id=session_game.chat_id
        )
        wait_answer.app.store.timer_manager.cancel_timer.assert_called_with(
            chat_id=chat_id, timer_type="30_second_for_answer"
        )

        session_game.current_round.question.is_answer_is_true(message.text)
        wait_answer.app.store.tg_api.send_message.assert_called_with(
            chat_id=chat_id,
            text=consts.IS_ANSWER_TRUE.format(
                answer=session_game.current_round.question.true_answer.title
            ),
        )
        wait_answer.round_store.set_is_correct_answer.assert_called_once_with(
            session_id=session_game.id, new_is_correct_answer=True
        )
        wait_answer.round_store.set_is_active_to_false.assert_called_once_with(
            session_id=session_game.id
        )
        wait_answer.check_and_notify_score.assert_called_once_with(
            session_id=session_game.id, chat_id=chat_id
        )
        wait_answer.next_quest.assert_not_called()