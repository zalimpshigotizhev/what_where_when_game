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
