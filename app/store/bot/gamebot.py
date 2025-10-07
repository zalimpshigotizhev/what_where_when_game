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


class GameProcessedError(Exception):
    pass


MAX_PLAYERS = 6
MIN_PLAYERS = 2


class BotBase:
    def __init__(self, app: "Application"):
        self.app = app
        self.unnecessary_messages: dict[int, list[int]] = {}
        self.handlers: list | None = None
        self._add_handlers_in_list()

    @property
    def game_s(self):
        return self.app.store.game_session

    @property
    def players(self):
        return self.app.store.players

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
        if (
            data.get("unnecessary_messages") is None
            or type(data.get("unnecessary_messages")) is not list
        ):
            data["unnecessary_messages"] = []

        data["unnecessary_messages"].append(message_id)
        await self.app.store.fsm.update_data(chat_id=chat_id, new_data=data)

    async def deleted_unnecessary_messages(self, chat_id: int):
        data = await self.app.store.fsm.get_data(chat_id)
        if data.get("unnecessary_messages") is None:
            return

        unnecessary_messages = data.get("unnecessary_messages")

        await self.app.store.tg_api.delete_messages(
            chat_id, unnecessary_messages
        )
        data["unnecessary_messages"] = []
        await self.app.store.fsm.update_data(chat_id=chat_id, new_data=data)

    async def cancel_game(self, chat_id: int, session_id: int):
        """Эта функция для отмены игры. Она общая для всех состояний
        chat_id:: Чат в котором проходит игра
        session_id:: Активный SessionModel который нужно отменить
        """
        await self.deleted_unnecessary_messages(chat_id=chat_id)
        await self.app.store.tg_api.send_message(
            chat_id=chat_id,
            text="Игра отменена, когда снова захотите "
            "интелектуально посоревноваться - я буду на месте 🦉",
        )
        await self.game_s.set_status(
            session_id=session_id, new_status=StatusSession.CANCELLED
        )

    async def ask_question(self, current_chat_id: int, session_id: int):
        """Эта функция для объявления вопроса и
        запуска таймера на одну минуту.
        callback:: принимает в себя через другого хендлера.
        context: принимает в себя через другого хендлера.
        """
        await self.deleted_unnecessary_messages(chat_id=current_chat_id)
        await self.app.store.fsm.set_state(
            chat_id=current_chat_id, new_state=GameState.QUESTION_DISCUTION
        )

        await self.app.store.tg_api.send_message(
            current_chat_id, text="Задается вопрос."
        )


class MainGameBot(BotBase):
    @filtered_handler(TypeFilter(CommandTG), TextFilter("/back"))
    async def handle_back(
        self, command: CommandTG, context: FSMContext
    ) -> None:
        """Обрабатывает сообщения в личных чатах"""
        chat_id = command.chat.id_
        user_id = command.from_.id_

        active_sess = await self.game_s.get_active_session_by_chat_id(
            chat_id=chat_id, inload_players=True
        )

        if active_sess is None:
            await self.app.store.tg_api.send_message(
                chat_id,
                "Игра не была запущена в этом чате. \n"
                "Запустите с помощью команды /start",
            )
            return

        dict_idtg_to_players = {
            player.user.id_tg: player
            for player in active_sess.players
            if player.is_active
        }
        player = dict_idtg_to_players.get(user_id)
        if player is not None:
            if player.is_captain:
                await self.cancel_game(
                    chat_id=chat_id, session_id=active_sess.id
                )
                return
            await self.app.store.tg_api.send_message(
                chat_id, "*Игру может отменить только капитан знатоков.* \n"
            )

    @filtered_handler(TypeFilter(CommandTG), TextFilter("/start"))
    async def handle_start_command(
        self, command: CommandTG, context: FSMContext
    ) -> None:
        """Обрабатывает сообщения в личных чатах"""
        chat_id = command.chat.id_

        active_sess = await self.game_s.get_active_session_by_chat_id(
            chat_id=chat_id
        )
        if active_sess is not None:
            if active_sess.status == StatusSession.PROCESSING:
                mess = await self.app.store.tg_api.send_message(
                    chat_id=chat_id,
                    text="*Сейчас игра уже идет в этом чате.*\n"
                    "Если хотите начать сначала, \n"
                    "то попросите капитана ввести команду: \n"
                    "/back",
                )
                await self.add_message_in_unnecessary_messages(
                    chat_id=chat_id, message_id=mess.message_id
                )
                return

        else:
            await self.game_s.create_session(
                chat_id=chat_id,
                status=StatusSession.PENDING,
            )

        mess = await self.app.store.tg_api.send_message(
            chat_id,
            "Добро пожаловать в игру! Используйте кнопки ниже для управления.",
            main_keyboard,
        )
        await self.add_message_in_unnecessary_messages(
            chat_id=chat_id, message_id=mess.message_id
        )

    @filtered_handler(TypeFilter(CallbackTG), CallbackDataFilter("start_game"))
    async def handle_start_game(
        self, callback: CallbackTG, context: FSMContext
    ) -> None:
        """Обрабатывает сообщения в личных чатах"""
        chat_id = callback.chat.id_

        curr_sess = await self.game_s.get_active_session_by_chat_id(
            chat_id=chat_id,
        )

        if curr_sess.status == StatusSession.PROCESSING:
            await self.app.store.tg_api.answer_callback_query(
                callback.id_, "Игра уже идет полным ходом!!!"
            )
            return

        await self.players.create_player(
            session_id=curr_sess.id,
            id_tg=callback.from_.id_,
            username_tg=callback.from_.username,
            is_captain=True,
        )

        await self.deleted_unnecessary_messages(chat_id)

        await self.app.store.tg_api.answer_callback_query(
            callback.id_, "Игра начинается! Вы будете капитаном."
        )
        mess = await self.app.store.tg_api.send_message(
            chat_id,
            f"Игрок *@{callback.from_.username}* "
            f"будет капитаном в команде знатоков.\n"
            f"Нажмите присоединиться к игре и ждите начало игры.",
            reply_markup=start_game_keyboard,
        )

        # Меняем статусы и состояние, также добавляем
        # mess.id в ненужные сообщение
        await self.game_s.set_status(
            session_id=curr_sess.id, new_status=StatusSession.PROCESSING
        )
        await self.app.store.fsm.set_state(
            chat_id=chat_id, new_state=GameState.WAITING_FOR_PLAYERS
        )
        await self.add_message_in_unnecessary_messages(
            chat_id=chat_id, message_id=mess.message_id
        )

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
        chat_id = callback.chat.id_
        user_id = callback.from_.id_
        curr_sess = await self.game_s.get_active_session_by_chat_id(
            chat_id=chat_id, inload_players=True
        )
        if curr_sess is None:
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_,
                text="Игры итак уже не существует!",
            )
            return

        active_connected_user_ids = [
            player.user.id_tg
            for player in curr_sess.players
            if player.is_active is True
        ]
        not_active_connected_user_ids = [
            player.user.id_tg
            for player in curr_sess.players
            if player.is_active is False
        ]

        if user_id in active_connected_user_ids:
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_,
                text="Вы уже участвуете в игре!",
            )
            return

        if user_id in not_active_connected_user_ids:
            await self.players.set_player_is_active(
                session_id=curr_sess.id, id_tg=user_id, new_active=True
            )
        else:
            await self.players.create_player(
                session_id=curr_sess.id,
                id_tg=user_id,
                username_tg=callback.from_.username,
            )

        await self.app.store.tg_api.answer_callback_query(
            callback_query_id=callback.id_, text="Теперь вы участник игры!"
        )

    @filtered_handler(
        TypeFilter(CallbackTG), CallbackDataFilter("start_game_from_captain")
    )
    async def handle_start_game_from_captain(
        self, callback: CallbackTG, context: FSMContext
    ) -> None:
        """Обрабатывает сообщения в личных чатах"""
        chat_id = callback.chat.id_
        user_id = callback.from_.id_

        curr_sess = await self.game_s.get_active_session_by_chat_id(
            chat_id=chat_id, inload_players=True
        )
        if curr_sess is None:
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_,
                text="Игры итак уже не существует!",
            )
            return

        dict_idtg_to_players = {
            player.user.id_tg: player
            for player in curr_sess.players
            if player.is_active
        }

        if user_id not in dict_idtg_to_players:
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_,
                text="Вы вообще не участвуйте в игре!",
            )
            return

        player = dict_idtg_to_players.get(user_id)

        if player.is_captain is True:
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_,
                text="Игра начинается GOOOOD LUCKK!",
            )

            mess = await self.app.store.tg_api.send_message(
                chat_id=callback.chat.id_,
                text="Капитан начал игру, готовы к первому вопросу?",
                reply_markup=are_ready_keyboard,
            )
            # Запускается таймер
            params_for_func = {
                "current_chat_id": chat_id,
                "session_id": curr_sess.id,
            }
            self.app.store.timer_manager.start_timer(
                chat_id=chat_id,
                timeout=5,
                timer_type="30_second_for_answer",
                callback=self.ask_question,
                # kwargs
                **params_for_func,
            )

            # Удаляются ненужные сообщения
            await self.deleted_unnecessary_messages(chat_id=callback.chat.id_)
            await self.add_message_in_unnecessary_messages(
                chat_id=callback.chat.id_, message_id=mess.message_id
            )

        elif player.is_captain is False:
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_,
                text="Игру может начать только капитан команды!",
            )

    @filtered_handler(TypeFilter(CallbackTG), CallbackDataFilter("finish_game"))
    async def handle_finish_game(
        self, callback: CallbackTG, context: FSMContext
    ) -> None:
        """Обрабатывает сообщения в личных чатах"""
        chat_id = callback.chat.id_
        user_id = callback.from_.id_

        curr_sess = await self.game_s.get_active_session_by_chat_id(
            chat_id=chat_id, inload_players=True
        )
        if curr_sess is None:
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_,
                text="Игры итак уже не существует!",
            )
            return

        dict_idtg_to_players = {
            player.user.id_tg: player
            for player in curr_sess.players
            if player.is_active
        }

        if user_id not in dict_idtg_to_players:
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_,
                text="Вы вообще не участвуйте в игре!",
            )
            return

        player = dict_idtg_to_players.get(user_id)
        if player.is_captain is True:
            await self.cancel_game(chat_id=chat_id, session_id=curr_sess.id)
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_,
                text="Вы капитан и вы заканчиваете игру!",
            )

        elif player.is_captain is False:
            await self.players.set_player_is_active(
                session_id=curr_sess.id, id_tg=user_id, new_active=False
            )
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_, text="Вы вышли из игры!"
            )


class AreReadyFirstRoundPlayersProcessGameBot(BotBase):
    @filtered_handler(TypeFilter(CallbackTG), CallbackDataFilter("ready"))
    async def handle_ready(
        self, callback: CallbackTG, context: FSMContext
    ) -> None:
        """Обрабатывает сообщения в личных чатах"""
        chat_id = callback.chat.id_
        user_id = callback.from_.id_

        curr_sess = await self.game_s.get_active_session_by_chat_id(
            chat_id=chat_id, inload_players=True
        )

        dict_idtg_to_players = {
            player.user.id_tg: player
            for player in curr_sess.players
            if player.is_active
        }

        if user_id not in dict_idtg_to_players:
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_,
                text="Вы не участник игры!",
            )
            return

        player = dict_idtg_to_players.get(user_id)

        if player.is_ready is True:
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_,
                text="Вы уже подтверждали свою готовность.",
            )
            return

        await self.app.store.tg_api.answer_callback_query(
            callback_query_id=callback.id_,
            text="Вы подтвердили свою готовность!",
        )
        await self.players.set_player_is_ready(
            session_id=curr_sess.id, id_tg=user_id, new_active=True
        )

        active_connected_user_ids = [
            player.user.id_tg
            for player in curr_sess.players
            if player.is_active is True
        ]
        are_ready_connected_user_ids = [
            player.user.id_tg
            for player in curr_sess.players
            if player.is_active is True and player.is_ready
        ]
        are_ready_connected_user_ids.append(user_id)

        # Если количество активных и готовых ровно участникам сессии,
        # то не дожидаемся таймера и запускаем игру, а таймер отменяем
        if len(active_connected_user_ids) == len(are_ready_connected_user_ids):
            # Отменяем таймер, который был запущен в
            # handle_start_game_from_captain
            self.app.store.timer_manager.cancel_timer(
                chat_id=chat_id, timer_type="30_second_for_answer"
            )

            await self.ask_question(
                current_chat_id=chat_id, session_id=curr_sess.id
            )


class QuestionDiscussionProcessGameBot(BotBase):
    pass


class VerdictCaptain(BotBase):
    pass


class WaitAnswer(BotBase):
    pass


class AreReadyNextRoundPlayersProcessGameBot(BotBase):
    pass
