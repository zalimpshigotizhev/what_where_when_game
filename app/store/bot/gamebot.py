import asyncio
from typing import TYPE_CHECKING

from app.bot.game.models import (
    GameState,
    PlayerModel,
    RoundModel,
    StatusSession,
)
from app.quiz.models import QuestionModel
from app.store.bot import consts
from app.store.bot.keyboards import (
    are_ready_keyboard,
    main_keyboard,
    start_game_keyboard,
)
from app.store.bot.utils import (
    CallbackDataFilter,
    StateFilter,
    TextFilter,
    TypeFilter,
    filtered_handler,
)
from app.store.tg_api.dataclasses import CallbackTG, CommandTG, MessageTG

if TYPE_CHECKING:
    from app.web.app import Application


class GameProcessedError(Exception):
    pass


MAX_PLAYERS = 6
MIN_PLAYERS = 1
# 1 минута
ARE_READY_TIMEOUT = 60
# 1 минута
QUESTION_DISCUTION_TIMEOUT = 1
# 2 минуты
VERDICT_CAPTAIN_TIMEOUT = 60

MAX_SCORE = 2


class BotBase:
    def __init__(self, app: "Application"):
        self.app = app
        self.unnecessary_messages: dict[int, list[int]] = {}
        self.handlers: list | None = None
        self._add_handlers_in_list()

    @property
    def round_store(self):
        return self.app.store.rounds

    @property
    def game_store(self):
        return self.app.store.game_session

    @property
    def player_store(self):
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

    async def cancel_game(
        self,
        current_chat_id: int,
        session_id: int,
        new_status: StatusSession = StatusSession.CANCELLED,
        text: str | None = None,
    ):
        """Эта функция для отмены игры. Она общая для всех состояний
        chat_id:: Чат в котором проходит игра
        session_id:: Активный SessionModel который нужно отменить
        """
        await self.deleted_unnecessary_messages(chat_id=current_chat_id)

        await self.game_store.set_status(
            session_id=session_id, new_status=new_status
        )
        await self.app.store.tg_api.send_message(
            chat_id=current_chat_id,
            text=text or consts.GAME_CLOSED,
        )

        self.app.store.timer_manager.clean_timers(chat_id=current_chat_id)

    async def ask_question(self, current_chat_id: int, session_id: int):
        """Эта функция для объявления вопроса и
        запуска таймера на одну минуту для обсуждения.
        :param current_chat_id id чата, где работает бот.
        :param session_id SessionModel.id активной сессии.
        """
        await self.deleted_unnecessary_messages(chat_id=current_chat_id)
        # Уничтожить всех кто не был готов к вопросу
        curr_sess = await self.game_store.get_active_session_by_chat_id(
            chat_id=current_chat_id, inload_players=True
        )
        players: list[PlayerModel] = curr_sess.players
        players_is_active_is_ready = []

        for player in players:
            if player.is_active is True and player.is_ready is False:
                if player.is_captain:
                    await self.cancel_game(
                        current_chat_id=current_chat_id, session_id=curr_sess.id
                    )
                    return
                await self.player_store.set_player_is_active(
                    session_id=curr_sess.id,
                    id_tg=player.user.username_tg,
                    new_active=False,
                )
            else:
                players_is_active_is_ready.append(player)

        if len(players_is_active_is_ready) < MIN_PLAYERS:
            mess = await self.app.store.tg_api.send_message(
                chat_id=current_chat_id, text=consts.NOT_ENOUGH_PLAYERS_MESSAGE
            )
            await self.add_message_in_unnecessary_messages(
                chat_id=current_chat_id, message_id=mess.message_id
            )

            await asyncio.sleep(2)
            await self.cancel_game(
                current_chat_id=current_chat_id, session_id=curr_sess.id
            )
            return

        await self.app.store.fsm.set_state(
            chat_id=current_chat_id, new_state=GameState.QUESTION_DISCUTION
        )

        rand_question: QuestionModel = (
            await self.app.store.quizzes.random_question()
        )

        new_round: RoundModel = await self.round_store.create_round(
            session_id=session_id, question_id=rand_question.id, is_active=True
        )
        await self.game_store.set_current_round(
            session_id=session_id, round_id=new_round.id
        )

        await self.app.store.tg_api.send_message(
            current_chat_id,
            text=consts.RUPOR_QUEST.format(
                theme=rand_question.theme.title, question=rand_question.title
            ),
        )

        self.app.store.timer_manager.start_timer(
            chat_id=current_chat_id,
            timeout=QUESTION_DISCUTION_TIMEOUT,
            callback=self.verdict_captain,
            timer_type="1_minute_question_discution",
            # kwargs
            current_chat_id=current_chat_id,
            session_id=session_id,
        )

    async def verdict_captain(self, current_chat_id: int, session_id: int):
        curr_sess = await self.game_store.get_active_session_by_chat_id(
            chat_id=current_chat_id, inload_players=True
        )

        players_for_answer = "\n".join(
            [f"· @{player.user.username_tg}" for player in curr_sess.players]
        )

        await self.app.store.tg_api.send_message(
            chat_id=current_chat_id,
            text=consts.MESSAGE_FOR_CAPTAIN.format(
                players_for_answer=players_for_answer
            ),
        )
        await self.app.store.fsm.set_state(
            chat_id=current_chat_id, new_state=GameState.VERDICT_CAPTAIN
        )
        # Устанавливаем таймер на 2 минуты
        # Если за две минуты капитан не выберет
        # отвечающего - игра отменится автоматически.
        self.app.store.timer_manager.start_timer(
            chat_id=current_chat_id,
            timeout=VERDICT_CAPTAIN_TIMEOUT,
            callback=self.cancel_game,
            timer_type="2_minute_verdict_captain",
            # kwargs
            current_chat_id=current_chat_id,
            session_id=curr_sess.id,
        )

    async def check_and_notify_score(
        self,
        session_id: int,
        chat_id: int,
    ):
        score = await self.game_store.gen_score(session_id=session_id)

        await self.app.store.tg_api.send_message(
            chat_id=chat_id,
            text=consts.RUPOR_SCORE.format(
                experts=score.get("experts"), bot=score.get("bot")
            ),
        )

        if score.get("experts") == MAX_SCORE:
            await self.app.store.tg_api.send_message(
                chat_id=chat_id, text=consts.YOUR_TEAM_WIN
            )
            await self.cancel_game(
                session_id=session_id,
                current_chat_id=chat_id,
                new_status=StatusSession.COMPLETED,
            )

        elif score.get("bot") == MAX_SCORE:
            await self.app.store.tg_api.send_message(
                chat_id=chat_id, text=consts.YOUR_TEAM_FAILE
            )

            await self.cancel_game(
                session_id=session_id,
                current_chat_id=chat_id,
                text=consts.GAME_COMPLETED,
                new_status=StatusSession.COMPLETED,
            )
        else:
            await self.next_quest(
                text=consts.ARE_YOU_READY_NEXT_QUEST,
                chat_id=chat_id,
                session_id=session_id,
            )

    async def is_answer_false(self, session_id: int, chat_id: int, text: str):
        await self.player_store.set_all_players_is_ready_false(
            session_id=session_id
        )
        if text:
            await self.app.store.tg_api.send_message(
                chat_id=chat_id,
                text=consts.NOT_PLAYER_CHOICE_CAP,
                reply_markup=are_ready_keyboard,
            )

        await self.round_store.set_is_correct_answer(
            session_id=session_id, new_is_correct_answer=False
        )
        await self.round_store.set_is_active_to_false(session_id=session_id)
        await self.check_and_notify_score(
            session_id=session_id, chat_id=chat_id
        )

        mess = await self.app.store.tg_api.send_message(
            chat_id=chat_id,
            text=consts.ARE_YOU_READY_NEXT_QUEST,
            reply_markup=are_ready_keyboard,
        )
        await self.add_message_in_unnecessary_messages(
            chat_id=chat_id, message_id=mess.message_id
        )

        await self.app.store.fsm.set_state(
            chat_id=chat_id, new_state=GameState.ARE_READY_NEXT_ROUND_PLAYERS
        )

    async def next_quest(self, text: str, chat_id: int, session_id: int):
        await self.player_store.set_all_players_is_ready_false(
            session_id=session_id
        )

        mess = await self.app.store.tg_api.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=are_ready_keyboard,
        )
        await self.add_message_in_unnecessary_messages(
            chat_id=chat_id, message_id=mess.message_id
        )

        await self.app.store.fsm.set_state(
            chat_id=chat_id, new_state=GameState.ARE_READY_NEXT_ROUND_PLAYERS
        )

        self.app.store.timer_manager.start_timer(
            chat_id=chat_id,
            timeout=ARE_READY_TIMEOUT,
            callback=self.ask_question,
            timer_type="30_second_are_ready",
            # kwargs
            current_chat_id=chat_id,
            session_id=session_id,
        )


class MainGameBot(BotBase):
    @filtered_handler(TypeFilter(CommandTG), TextFilter("/back"))
    async def handle_back(
        self, command: CommandTG, context: GameState | None
    ) -> None:
        """Обрабатывает сообщения в личных чатах"""
        chat_id = command.chat.id_
        user_id = command.from_.id_

        active_sess = await self.game_store.get_active_session_by_chat_id(
            chat_id=chat_id, inload_players=True
        )

        if active_sess is None:
            await self.app.store.tg_api.send_message(
                chat_id=chat_id, text=consts.DONT_EXIST_GAME_IN_CHAT
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
                    current_chat_id=chat_id, session_id=active_sess.id
                )
                return
            await self.app.store.tg_api.send_message(
                text=consts.CANCEL_GAME_ONLY_CAP,
                chat_id=chat_id,
            )

    @filtered_handler(TypeFilter(CommandTG), TextFilter("/start"))
    async def handle_start_command(
        self, command: CommandTG, context: GameState | None
    ) -> None:
        """Обрабатывает сообщения в личных чатах"""
        chat_id = command.chat.id_

        active_sess = await self.game_store.get_active_session_by_chat_id(
            chat_id=chat_id
        )
        if active_sess is not None:
            if active_sess.status == StatusSession.PROCESSING:
                mess = await self.app.store.tg_api.send_message(
                    chat_id=chat_id,
                    text=consts.EXIST_GAME_CAN_EXIT,
                )
                await self.add_message_in_unnecessary_messages(
                    chat_id=chat_id, message_id=mess.message_id
                )
                return

        else:
            await self.game_store.create_session(
                chat_id=chat_id,
                status=StatusSession.PENDING,
            )

        mess = await self.app.store.tg_api.send_message(
            chat_id=chat_id,
            text=consts.WELCOME_TO_GAME,
            reply_markup=main_keyboard,
        )
        await self.add_message_in_unnecessary_messages(
            chat_id=chat_id, message_id=mess.message_id
        )

    @filtered_handler(TypeFilter(CallbackTG), CallbackDataFilter("start_game"))
    async def handle_start_game(
        self, callback: CallbackTG, context: GameState | None
    ) -> None:
        """Обрабатывает сообщения в личных чатах"""
        chat_id = callback.chat.id_

        curr_sess = await self.game_store.get_active_session_by_chat_id(
            chat_id=chat_id,
        )

        if curr_sess.status == StatusSession.PROCESSING:
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_, text=consts.GAME_IS_EXIST
            )
            return

        await self.player_store.create_player(
            session_id=curr_sess.id,
            id_tg=callback.from_.id_,
            username_tg=callback.from_.username,
            is_captain=True,
        )

        await self.deleted_unnecessary_messages(chat_id)

        await self.app.store.tg_api.answer_callback_query(
            callback_query_id=callback.id_,
            text=consts.ALERT_FOR_CAP,
        )
        mess = await self.app.store.tg_api.send_message(
            chat_id=chat_id,
            text=consts.INFORMATION_ABOUT_CAP.format(
                username=callback.from_.username
            ),
            reply_markup=start_game_keyboard,
        )

        # Меняем статусы и состояние, также добавляем
        # mess.id в ненужные сообщение
        await self.game_store.set_status(
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
        self, callback: CallbackTG, context: GameState | None
    ) -> None:
        """Обрабатывает сообщения в личных чатах"""
        bot_message = await self.app.store.tg_api.send_message(
            callback.chat.id_, consts.RULES_INFO
        )
        await self.add_message_in_unnecessary_messages(
            chat_id=callback.chat.id_, message_id=bot_message.message_id
        )

    @filtered_handler(TypeFilter(CallbackTG), CallbackDataFilter("show_rating"))
    async def handle_show_rating(
        self, callback: CallbackTG, context: GameState | None
    ) -> None:
        """Обрабатывает сообщения в личных чатах"""
        bot_message = await self.app.store.tg_api.send_message(
            callback.chat.id_, consts.RATING_INFO
        )
        await self.add_message_in_unnecessary_messages(
            chat_id=callback.chat.id_, message_id=bot_message.message_id
        )


class WaitingPlayersProcessGameBot(BotBase):
    @filtered_handler(
        TypeFilter(CallbackTG),
        CallbackDataFilter("join_game"),
        StateFilter(GameState.WAITING_FOR_PLAYERS),
    )
    async def handle_join_game(
        self, callback: CallbackTG, context: GameState | None
    ) -> None:
        """Обрабатывает сообщения в личных чатах"""
        chat_id = callback.chat.id_
        user_id = callback.from_.id_
        curr_sess = await self.game_store.get_active_session_by_chat_id(
            chat_id=chat_id, inload_players=True
        )
        if curr_sess is None:
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_,
                text=consts.GAME_DONT_EXIST,
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
                text=consts.YOU_DONT_PLAYER,
            )
            return

        if user_id in not_active_connected_user_ids:
            await self.player_store.set_player_is_active(
                session_id=curr_sess.id, id_tg=user_id, new_active=True
            )
        else:
            await self.player_store.create_player(
                session_id=curr_sess.id,
                id_tg=user_id,
                username_tg=callback.from_.username,
            )

        await self.app.store.tg_api.answer_callback_query(
            callback_query_id=callback.id_, text=consts.YOU_PLAYER_WITH_GAME
        )

    @filtered_handler(
        TypeFilter(CallbackTG),
        CallbackDataFilter("start_game_from_captain"),
        StateFilter(GameState.WAITING_FOR_PLAYERS),
    )
    async def handle_start_game_from_captain(
        self, callback: CallbackTG, context: GameState | None
    ) -> None:
        """Обрабатывает сообщения в личных чатах"""
        chat_id = callback.chat.id_
        user_id = callback.from_.id_

        curr_sess = await self.game_store.get_active_session_by_chat_id(
            chat_id=chat_id, inload_players=True
        )
        if curr_sess is None:
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_,
                text=consts.GAME_DONT_EXIST,
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
                text=consts.YOU_DONT_PLAYER,
            )
            return

        player = dict_idtg_to_players.get(user_id)

        if player.is_captain is True:
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_,
                text=consts.STARTED_GAME_FOR_CAP,
            )
            await self.deleted_unnecessary_messages(chat_id=callback.chat.id_)

            await self.next_quest(
                text=consts.ARE_YOU_READY_FIRST_QUEST,
                chat_id=chat_id,
                session_id=curr_sess.id,
            )

        elif player.is_captain is False:
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_,
                text=consts.GAME_START_ONLY_CAP,
            )

    @filtered_handler(
        TypeFilter(CallbackTG),
        CallbackDataFilter("finish_game"),
        StateFilter(GameState.WAITING_FOR_PLAYERS),
    )
    async def handle_finish_game(
        self, callback: CallbackTG, context: GameState | None
    ) -> None:
        """Обрабатывает сообщения в личных чатах"""
        chat_id = callback.chat.id_
        user_id = callback.from_.id_

        curr_sess = await self.game_store.get_active_session_by_chat_id(
            chat_id=chat_id, inload_players=True
        )
        if curr_sess is None:
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_,
                text=consts.GAME_DONT_EXIST,
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
                text=consts.YOU_DONT_PLAYER,
            )
            return

        player = dict_idtg_to_players.get(user_id)
        if player.is_captain is True:
            await self.cancel_game(
                current_chat_id=chat_id, session_id=curr_sess.id
            )
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_,
                text=consts.YOU_CAP_AND_YOU_FINISH_GAME,
            )

        elif player.is_captain is False:
            await self.player_store.set_player_is_active(
                session_id=curr_sess.id, id_tg=user_id, new_active=False
            )
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_, text=consts.YOU_EXIT_GAME
            )


class AreReadyFirstRoundPlayersProcessGameBot(BotBase):
    @filtered_handler(
        TypeFilter(CallbackTG),
        CallbackDataFilter("ready"),
        StateFilter(GameState.ARE_READY_NEXT_ROUND_PLAYERS),
    )
    async def handle_ready(
        self, callback: CallbackTG, context: GameState | None
    ) -> None:
        """Обрабатывает сообщения в личных чатах"""
        chat_id = callback.chat.id_
        user_id = callback.from_.id_

        curr_sess = await self.game_store.get_active_session_by_chat_id(
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
                text=consts.YOU_DONT_PLAYER,
            )
            return

        player = dict_idtg_to_players.get(user_id)

        if player.is_ready is True:
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_,
                text=consts.ALREADY_CONFIRMED_READINESS,
            )
            return

        await self.app.store.tg_api.answer_callback_query(
            callback_query_id=callback.id_,
            text=consts.YOU_APPLY_READY,
        )
        await self.player_store.set_player_is_ready(
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

        await asyncio.sleep(0.1)
        # Если количество активных и готовых равно участникам сессии,
        # то не дожидаемся таймера и запускаем игру, а таймер завершаем
        if len(active_connected_user_ids) == len(are_ready_connected_user_ids):
            # Отменяем таймер, который был запущен в
            # handle_start_game_from_captain
            self.app.store.timer_manager.cancel_timer(
                chat_id=chat_id, timer_type="30_second_are_ready"
            )

            await self.ask_question(
                current_chat_id=chat_id, session_id=curr_sess.id
            )


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


class VerdictCaptain(BotBase):
    @filtered_handler(
        TypeFilter(MessageTG), StateFilter(GameState.VERDICT_CAPTAIN)
    )
    async def handle_verdict_captain(
        self, message: MessageTG, context: GameState | None
    ) -> None:
        chat_id = message.chat.id_
        if message.entities is None:
            mess = await self.app.store.tg_api.send_message(
                chat_id=chat_id, text=consts.CAPTAIN_INSTUCTION
            )
            await self.add_message_in_unnecessary_messages(
                chat_id=chat_id, message_id=mess.message_id
            )
            return

        for entity in message.entities:
            if entity.type == "mention":
                curr_sess = await self.game_store.get_active_session_by_chat_id(
                    chat_id=chat_id,
                )

                curr_player = await self.player_store.get_player_by_idtg(
                    session_id=curr_sess.id, id_tg=message.from_.id_
                )
                if curr_player is not None and not curr_player.is_captain:
                    mess = await self.app.store.tg_api.send_message(
                        chat_id=chat_id, text=consts.WARNING_CAPTAIN_ONLY
                    )
                    await self.add_message_in_unnecessary_messages(
                        chat_id=chat_id, message_id=mess.message_id
                    )
                    return

                chosen_player = (
                    await self.player_store.get_player_by_username_tg(
                        session_id=curr_sess.id,
                        username_tg=message.text[
                            entity.offset + 1 : entity.offset + entity.length
                        ],
                    )
                )

                if (
                    chosen_player is not None
                    and chosen_player.is_active
                    and chosen_player.is_ready
                ):
                    self.app.store.timer_manager.cancel_timer(
                        chat_id=chat_id, timer_type="2_minute_verdict_captain"
                    )
                    await self.round_store.set_answer_player_id(
                        session_id=curr_sess.id,
                        answer_player_id=chosen_player.id,
                    )
                    await self.app.store.fsm.set_state(
                        chat_id=chat_id, new_state=GameState.WAIT_ANSWER
                    )
                    mess = await self.app.store.tg_api.send_message(
                        chat_id=chat_id,
                        text=consts.PLAYER_QUESTION_INSTRUCTION.format(
                            player=chosen_player.user.username_tg
                        ),
                    )
                    await self.add_message_in_unnecessary_messages(
                        chat_id=chat_id, message_id=mess.message_id
                    )
                    return
                mess = await self.app.store.tg_api.send_message(
                    chat_id=chat_id, text=consts.WARNING_CAP_DONT_EXIST_PLAYER
                )
                await self.add_message_in_unnecessary_messages(
                    chat_id=chat_id, message_id=mess.message_id
                )


class WaitAnswer(BotBase):
    @filtered_handler(TypeFilter(MessageTG), StateFilter(GameState.WAIT_ANSWER))
    async def handle_wait_answer(
        self, message: MessageTG, context: GameState | None
    ) -> None:
        """В этом состоянии мы должны получить ответ от выбранного
        капитаном игрока, если получаем сообщение от другого участника
        сообщение бот присваивает балл себе
        (текущий Round.is_correct_answer=False).
        Если Player.id == Round.answer_player_id и ответ корректный,
        то балл присваивается команде знатоков
        (текущий Round.is_correct_answer=True).

        В любом исходе Round.is_active меняется на False и раунд больше
        не является текущим.

        :param message:
        :param context:
        :return:
        """
        chat_id = message.chat.id_
        curr_sess = await self.game_store.get_active_session_by_chat_id(
            chat_id=chat_id,
        )
        current_round: RoundModel = curr_sess.current_round
        question: QuestionModel = current_round.question
        player: PlayerModel = current_round.answer_player

        if player.user.username_tg != message.from_.username:
            await self.is_answer_false(
                session_id=curr_sess.id,
                chat_id=chat_id,
            )
            return

        is_correct_answer = question.is_answer_is_true(message.text)
        if question.true_answer.description:
            await self.app.store.tg_api.send_message(
                chat_id=chat_id, text=question.true_answer.description
            )

        if is_correct_answer:
            await self.app.store.tg_api.send_message(
                chat_id=chat_id,
                text=consts.IS_ANSWER_TRUE.format(
                    answer=question.true_answer.title
                ),
            )

        else:
            await self.app.store.tg_api.send_message(
                chat_id=chat_id,
                text=consts.IS_ANSWER_FALSE.format(
                    answer=question.true_answer.title
                ),
            )

        await self.round_store.set_is_correct_answer(
            session_id=curr_sess.id, new_is_correct_answer=is_correct_answer
        )
        await self.round_store.set_is_active_to_false(session_id=curr_sess.id)

        await self.check_and_notify_score(
            session_id=curr_sess.id, chat_id=chat_id
        )
