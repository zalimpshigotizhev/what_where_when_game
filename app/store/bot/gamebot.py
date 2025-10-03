from typing import TYPE_CHECKING

from app.store.bot import replicas
from app.store.bot.fsm import FSMContext
from app.store.bot.keyboards import main_keyboard, start_game_keyboard
from app.store.bot.utils import (
    CallbackDataFilter,
    TextFilter,
    TypeFilter,
    filtered_handler,
)
from app.store.tg_api.dataclasses import CallbackTG, CommandTG

if TYPE_CHECKING:
    from app.web.app import Application


class BotBase:
    def __init__(self, app: "Application"):
        self.app = app

        self.unnecessary_messages: list | None = None
        self.handlers: list | None = None
        self._add_handlers_in_list()

    def _add_handlers_in_list(self):
        if self.handlers is None:
            self.handlers = []
            for attr_name in dir(self):
                if attr_name.startswith("handle_"):
                    attr = getattr(self, attr_name)
                    if callable(attr):
                        self.handlers.append(attr)
        return self.handlers

    def add_message_in_unnecessary_messages(self, message_id: int):
        if self.unnecessary_messages is None:
            self.unnecessary_messages = []
        self.unnecessary_messages.append(message_id)


class MainGameBot(BotBase):
    @filtered_handler(TypeFilter(CommandTG), TextFilter("/start"))
    async def handle_start_command(
        self, command: CommandTG, context: FSMContext
    ) -> None:
        """Обрабатывает сообщения в личных чатах"""
        bot_message = await self.app.store.tg_api.send_message(
            command.chat.id_,
            "Добро пожаловать в игру! Используйте кнопки ниже для управления.",
            main_keyboard,
        )
        self.add_message_in_unnecessary_messages(
            message_id=bot_message.message_id
        )

    @filtered_handler(TypeFilter(CallbackTG), CallbackDataFilter("start_game"))
    async def handle_start_game(
        self, callback: CallbackTG, context: FSMContext
    ) -> None:
        """Обрабатывает сообщения в личных чатах"""
        await self.app.store.tg_api.delete_messages(
            callback.chat.id_, self.unnecessary_messages
        )
        await self.app.store.tg_api.delete_message(
            callback.chat.id_, callback.message.message_id
        )
        await self.app.store.tg_api.answer_callback_query(
            callback.id_, "Игра начинается! Вы будете капитаном."
        )
        await self.app.store.tg_api.send_message(
            callback.chat.id_,
            f"Игрок *@{callback.from_.username}* "
            f"будет капитаном в команде знатоков.\n"
            f"Нажмите присоединиться к игре и ждите начало игры.",
            reply_markup=start_game_keyboard,
        )

    @filtered_handler(TypeFilter(CallbackTG), CallbackDataFilter("show_rules"))
    async def handle_show_rules(
        self, callback: CallbackTG, context: FSMContext
    ) -> None:
        """Обрабатывает сообщения в личных чатах"""
        bot_message = await self.app.store.tg_api.send_message(
            callback.chat.id_, replicas.RULES_INFO
        )
        self.add_message_in_unnecessary_messages(
            message_id=bot_message.message_id
        )

    @filtered_handler(TypeFilter(CallbackTG), CallbackDataFilter("show_rating"))
    async def handle_show_rating(
        self, callback: CallbackTG, context: FSMContext
    ) -> None:
        """Обрабатывает сообщения в личных чатах"""
        bot_message = await self.app.store.tg_api.send_message(
            callback.chat.id_, replicas.RATING_INFO
        )
        self.add_message_in_unnecessary_messages(
            message_id=bot_message.message_id
        )


class WaitingPlayersProcessGameBot(BotBase):
    pass


class AreReadyFirstRoundPlayersProcessGameBot(BotBase):
    pass


class QuestionDiscussionProcessGameBot(BotBase):
    pass


class VerdictCaptain(BotBase):
    pass


class WaitAnswer(BotBase):
    pass


class AreReadyNextRoundPlayersProcessGameBot(BotBase):
    pass
