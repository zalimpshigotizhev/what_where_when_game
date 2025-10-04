from typing import TYPE_CHECKING

from app.bot.game.models import GameState, StatusSession
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
        self.fsm = FSMContext()

        self.unnecessary_messages: dict[int, list[int]] = {}
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

    def add_message_in_unnecessary_messages(
        self, chat_id: int, message_id: int
    ):
        if chat_id not in self.unnecessary_messages:
            self.unnecessary_messages[chat_id] = []
        self.unnecessary_messages[chat_id].append(message_id)

    async def deleted_unnecessary_messages(self, chat_id: int):
        if self.unnecessary_messages.get(chat_id):
            await self.app.store.tg_api.delete_messages(
                chat_id, self.unnecessary_messages[chat_id]
            )
            self.unnecessary_messages[chat_id] = []


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
            chat_id=command.chat.id_, message_id=bot_message.message_id
        )

    @filtered_handler(TypeFilter(CallbackTG), CallbackDataFilter("start_game"))
    async def handle_start_game(
        self, callback: CallbackTG, context: FSMContext
    ) -> None:
        """Обрабатывает сообщения в личных чатах"""
        session_game_store = self.app.store.session_game
        new_session_game = await session_game_store.create_session_game(
            chat_id=callback.chat.id_,
            status=StatusSession.PENDING,
            current_state=GameState.WAITING_FOR_PLAYERS,
            current_round_id=None,
        )
        await session_game_store.create_player(
            session_id=new_session_game.id,
            id_tg=callback.from_.id_,
            username_tg=callback.from_.username,
            is_captain=True,
        )
        self.add_message_in_unnecessary_messages(
            chat_id=callback.chat.id_, message_id=callback.message.message_id
        )
        await self.deleted_unnecessary_messages(callback.chat.id_)

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
            chat_id=callback.chat.id_, message_id=bot_message.message_id
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
            chat_id=callback.chat.id_, message_id=bot_message.message_id
        )


class WaitingPlayersProcessGameBot(BotBase):
    @filtered_handler(TypeFilter(CallbackTG), CallbackDataFilter("join_game"))
    async def handle_join_game(
        self, callback: CallbackTG, context: FSMContext
    ) -> None:
        """Обрабатывает сообщения в личных чатах"""
        session_game = self.app.store.session_game
        user_tg = callback.from_

        current_session = await session_game.get_curr_game_session_by_chat_id(
            chat_id=callback.chat.id_
        )

        if await session_game.is_user_in_session(
            user_tg.id_, current_session.id
        ):
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_,
                text="Вы уже учавствуете в игре!",
            )
        else:
            await session_game.create_player(
                session_id=current_session.id,
                id_tg=callback.from_.id_,
                username_tg=callback.from_.username,
            )
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_, text="Теперь вы участник игры!"
            )

    # @filtered_handler(
    #     TypeFilter(CallbackTG),
    #     CallbackDataFilter("start_game_from_captain")
    # )
    # async def handle_start_game_from_captain(
    #         self,
    #         callback: CallbackTG,
    #         context: FSMContext
    # ) -> None:
    #     """Обрабатывает сообщения в личных чатах"""
    #     ...
    #
    # @filtered_handler(
    #     TypeFilter(CallbackTG),
    #     CallbackDataFilter("finish_game")
    # )
    # async def handle_finish_game(
    #         self,
    #         callback: CallbackTG,
    #         context: FSMContext
    # ) -> None:
    #     """Обрабатывает сообщения в личных чатах"""
    #     ...


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
