import pytest

from app.bot.game.models import GameState
from app.store.bot.gamebot.quest_disscution_state import QuestionDiscussionProcessGameBot


class TestQuestionDiscussionState:
    @pytest.fixture
    def quest_diss(self, mock_app):
        return QuestionDiscussionProcessGameBot(mock_app)

    @pytest.mark.asyncio
    async def test_initialization(self, quest_diss, mock_app):
        """Тест инициализации BotBase"""
        assert quest_diss.app == mock_app
        assert quest_diss.handlers is not None

        assert quest_diss.game_store == quest_diss.app.store.game_session

    @pytest.mark.asyncio
    async def test_handle_question_discution(
            self,
            quest_diss,
            message,
    ):
        """
        Тест на
        """
        await quest_diss.handle_question_discution(
            message, context=GameState.QUESTION_DISCUTION
        )