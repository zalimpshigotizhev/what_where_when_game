from app.bot.game.models import GameState
from app.store.bot.gamebot.base import BotBase
from app.store.bot.utils import (
    StateFilter,
    TypeFilter,
    filtered_handler,
)
from app.store.tg_api.dataclasses import CallbackTG, MessageTG


class QuestionDiscussionProcessGameBot(BotBase):
    @filtered_handler(
        TypeFilter(MessageTG), StateFilter(GameState.QUESTION_DISCUTION)
    )
    async def handle_question_discution(
        self, callback: CallbackTG, context: GameState | None
    ) -> None:
        # Таймер запущен.
        # Даем возможность обсудить вопрос среди игроков.
        pass
