from app.bot.game.models import GameState
from app.store.bot.gamebot.base import BotBase
from app.store.bot.utils import (
    StateFilter,
    TypeFilter,
    filtered_handler,
)
from app.store.tg_api.dataclasses import MessageTG


class QuestionDiscussionProcessGameBot(BotBase):
    @filtered_handler(
        TypeFilter(MessageTG), StateFilter(GameState.QUESTION_DISCUTION)
    )
    async def handle_question_discution(
        self, message: MessageTG, context: GameState | None
    ) -> None:
        # Таймер запущен.
        # Даем возможность обсудить вопрос среди игроков.
        pass

    # TODO: Добавить Хэндлер Который уничтожает сообщения
    # TODO: Добавить FilterSet для filtered_handler которая срабатывает при определенных State
    # @filtered_handler(
    #     TypeFilter(MessageTG)
    # )
    # async def handle_question_discution(
    #     self, message: MessageTG, context: GameState | None
    # ) -> None:
    #     # Таймер запущен.
    #     # Даем возможность обсудить вопрос среди игроков.
    #     await self.app.store.tg_api.delete_message(
    #         chat_id=message.chat.id_,
    #         message_id=message.message_id
    #     )
    #     pass
