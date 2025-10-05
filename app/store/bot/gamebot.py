from typing import TYPE_CHECKING

from app.bot.game.models import GameState, StatusSession
from app.store.bot import replicas
from app.store.bot.fsm import FSMContext
from app.store.bot.keyboards import (
    are_ready_keyboard,
    main_keyboard,
    start_game_keyboard,
)
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

    async def add_message_in_unnecessary_messages(
        self, chat_id: int, message_id: int
    ) -> None:
        data = await self.app.store.fsm.get_data(chat_id)
        if (data.get("unnecessary_messages") is None or
                type(data.get("unnecessary_messages")) is not list):
            data["unnecessary_messages"] = []

        data["unnecessary_messages"].append(message_id)
        await self.app.store.fsm.update_data(
            chat_id=chat_id, new_data=data
        )

    async def deleted_unnecessary_messages(self, chat_id: int):
        data = await self.app.store.fsm.get_data(chat_id)
        if data.get("unnecessary_messages") is None:
            return

        unnecessary_messages = data.get("unnecessary_messages")

        await self.app.store.tg_api.delete_messages(
            chat_id, unnecessary_messages
        )
        data["unnecessary_messages"] = []
        await self.app.store.fsm.update_data(
            chat_id=chat_id, new_data=data
        )


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
        game_store = self.app.store.session_game
        await game_store.create_session_game(
            chat_id=command.chat.id_,
            status=StatusSession.PENDING,
            current_state=GameState.WAITING_FOR_PLAYERS,
            current_round_id=None,
        )
        await self.add_message_in_unnecessary_messages(
            chat_id=command.chat.id_, message_id=bot_message.message_id
        )

    @filtered_handler(TypeFilter(CallbackTG), CallbackDataFilter("start_game"))
    async def handle_start_game(
        self, callback: CallbackTG, context: FSMContext
    ) -> None:
        """Обрабатывает сообщения в личных чатах"""
        game_store = self.app.store.session_game
        curr_sess = await game_store.get_curr_game_session_by_chat_id(
            chat_id=callback.chat.id_
        )
        await game_store.create_player(
            session_game_id=curr_sess.id,
            id_tg=callback.from_.id_,
            username_tg=callback.from_.username,
            is_captain=True,
        )
        await self.add_message_in_unnecessary_messages(
            chat_id=callback.chat.id_, message_id=callback.message.message_id
        )
        await self.deleted_unnecessary_messages(callback.chat.id_)

        await self.app.store.tg_api.answer_callback_query(
            callback.id_, "Игра начинается! Вы будете капитаном."
        )
        mess = await self.app.store.tg_api.send_message(
            callback.chat.id_,
            f"Игрок *@{callback.from_.username}* "
            f"будет капитаном в команде знатоков.\n"
            f"Нажмите присоединиться к игре и ждите начало игры.",
            reply_markup=start_game_keyboard,
        )

        await self.add_message_in_unnecessary_messages(mess.message_id)

    @filtered_handler(TypeFilter(CallbackTG), CallbackDataFilter("show_rules"))
    async def handle_show_rules(
        self, callback: CallbackTG, context: FSMContext
    ) -> None:
        """Обрабатывает сообщения в личных чатах"""
        bot_message = await self.app.store.tg_api.send_message(
            callback.chat.id_, replicas.RULES_INFO
        )
        await self.add_message_in_unnecessary_messages(
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
        await self.add_message_in_unnecessary_messages(
            chat_id=callback.chat.id_, message_id=bot_message.message_id
        )


class WaitingPlayersProcessGameBot(BotBase):
    @filtered_handler(TypeFilter(CallbackTG), CallbackDataFilter("join_game"))
    async def handle_join_game(
        self, callback: CallbackTG, context: FSMContext
    ) -> None:
        """Обрабатывает сообщения в личных чатах"""
        game_store = self.app.store.session_game

        current_session = await game_store.get_curr_game_session_by_chat_id(
            chat_id=callback.chat.id_
        )
        participants = await game_store.get_session_participants(
            session_game_id=current_session.id,
            active_only=True
        )
        ids_participant: list[int] = [
            partic.user.username_id_tg for partic in participants
        ]

        if callback.from_.id_ in ids_participant:
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_,
                text="Вы уже учавствуете в игре!",
            )
        else:
            await game_store.create_player(
                session_game_id=current_session.id,
                id_tg=callback.from_.id_,
                username_tg=callback.from_.username,
            )
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_, text="Теперь вы участник игры!"
            )

    @filtered_handler(
        TypeFilter(CallbackTG),
        CallbackDataFilter("start_game_from_captain")
    )
    async def handle_start_game_from_captain(
            self,
            callback: CallbackTG,
            context: FSMContext
    ) -> None:
        """Обрабатывает сообщения в личных чатах"""
        game_store = self.app.store.session_game

        current_session = await game_store.get_curr_game_session_by_chat_id(
            chat_id=callback.chat.id_
        )

        player = await game_store.get_player(
            session_game_id=current_session.id,
            user_id=callback.from_.id_
        )

        if (player is None or
            player.is_active is None or
            player.is_active is False):
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_,
                text="Вы вообще не участвуйте в игре!"
            )

        elif player.is_captain is True:
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_,
                text="Игра начинается GOOOOD LUCKK!"
            )

            await self.deleted_unnecessary_messages(chat_id=callback.chat.id_)
            mess = await self.app.store.tg_api.send_message(
                chat_id=callback.chat.id_,
                text="Капитан начал игру, готовы к первому вопросу?",
                reply_markup=are_ready_keyboard
            )
            await self.add_message_in_unnecessary_messages(
                chat_id=callback.chat.id_,
                message_id=mess.message_id
            )

        elif player.is_captain is False:
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_,
                text="Игру может начать только капитан команды!"
            )

    @filtered_handler(
        TypeFilter(CallbackTG),
        CallbackDataFilter("finish_game")
    )
    async def handle_finish_game(
            self,
            callback: CallbackTG,
            context: FSMContext
    ) -> None:
        """Обрабатывает сообщения в личных чатах"""
        game_store = self.app.store.session_game

        current_session = await game_store.get_curr_game_session_by_chat_id(
            chat_id=callback.chat.id_
        )

        player = await game_store.get_player(
            session_game_id=current_session.id,
            user_id=callback.from_.id_
        )

        if (player is None or
            player.is_active is None or
            player.is_active is False):
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_,
                text="Вы итак не участвуйте в игре!"
            )
        elif player.is_captain is True:
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_,
                text="Вы капитан и вы заканчиваете игру!"
            )
        elif player.is_captain is False:
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_, text="Вы вышли из игры!"
            )


class AreReadyFirstRoundPlayersProcessGameBot(BotBase):
    @filtered_handler(
        TypeFilter(CallbackTG),
        CallbackDataFilter("ready")
    )
    async def handle_finish_game(
            self,
            callback: CallbackTG,
            context: FSMContext
    ) -> None:
        """Обрабатывает сообщения в личных чатах"""


class QuestionDiscussionProcessGameBot(BotBase):
    pass


class VerdictCaptain(BotBase):
    pass


class WaitAnswer(BotBase):
    pass


class AreReadyNextRoundPlayersProcessGameBot(BotBase):
    pass
