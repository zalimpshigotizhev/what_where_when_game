from app.bot.game.models import GameState, StatusSession
from app.store.bot import consts
from app.store.bot.gamebot.base import BotBase
from app.store.bot.keyboards import main_keyboard, start_game_keyboard
from app.store.bot.utils import (
    CallbackDataFilter,
    TextFilter,
    TypeFilter,
    filtered_handler,
)
from app.store.tg_api.dataclasses import CallbackTG, CommandTG


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
        if context == GameState.INACTIVE or player is not None:
            if context == GameState.INACTIVE or player.is_captain:
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
        text = consts.WELCOME_TO_GAME
        reply = main_keyboard

        active_sess = await self.game_store.get_active_session_by_chat_id(
            chat_id=chat_id
        )
        if active_sess is None:
            await self.game_store.create_session(
                    chat_id=chat_id,
                    status=StatusSession.PENDING,
                )

        elif active_sess.status == StatusSession.PENDING:
            pass

        elif active_sess.status == StatusSession.PROCESSING:
            text = consts.EXIST_GAME_CAN_EXIT
            reply = None

        mess = await self.app.store.tg_api.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply,
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
        if curr_sess is None:
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_, text=consts.THIS_GAME_COMPLETED
            )
            return
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

        await self.deleted_unnecessary_messages(chat_id=chat_id)

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
            chat_id=callback.chat.id_, text=consts.RULES_INFO
        )
        await self.add_message_in_unnecessary_messages(
            chat_id=callback.chat.id_, message_id=bot_message.message_id
        )

    @filtered_handler(TypeFilter(CallbackTG), CallbackDataFilter("show_rating"))
    async def handle_show_rating(
        self, callback: CallbackTG, context: GameState | None
    ) -> None:
        """Выдает рейтинг чата"""
        completed_sessions = await self.game_store.get_completed_sessions(
            chat_id=callback.chat.id_
        )
        if completed_sessions is None or len(completed_sessions) == 0:
            experts = 0
            bot = 0

        else:
            last_game_sess = completed_sessions[0]
            score: dict = await self.game_store.gen_score(
                session_id=last_game_sess.id
            )
            experts = score.get("experts")
            bot = score.get("bot")

        bot_message = await self.app.store.tg_api.send_message(
            callback.chat.id_,
            consts.RATING_INFO.format(
                count=len(completed_sessions),
                experts=experts,
                bot=bot,
            ),
        )
        await self.add_message_in_unnecessary_messages(
            chat_id=callback.chat.id_, message_id=bot_message.message_id
        )
