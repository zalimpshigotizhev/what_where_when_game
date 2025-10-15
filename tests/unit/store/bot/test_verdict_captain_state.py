import pytest

from app.store.bot.gamebot.verdict_captain_state import VerdictCaptain


class TestVerdictCaptainState:
    @pytest.fixture
    def verdict_cap(self, mock_app):
        return VerdictCaptain(mock_app)

    @pytest.mark.asyncio
    async def test_initialization(self, verdict_cap, mock_app):
        """Тест инициализации BotBase"""
        assert verdict_cap.app == mock_app
        assert verdict_cap.handlers is not None

        assert verdict_cap.game_store == verdict_cap.app.store.game_session

    @pytest.mark.asyncio
    async def test_handle_verdict_captain(self):
        """
        Тест на
        """
        pass