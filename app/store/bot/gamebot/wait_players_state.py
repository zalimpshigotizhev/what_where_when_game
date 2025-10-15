from app.bot.game.models import GameState
from app.store.bot import consts
from app.store.bot.consts import MIN_PLAYERS, PLAYER_JOINED, MAX_PLAYERS
from app.store.bot.gamebot.base import BotBase
from app.store.bot.utils import (
    CallbackDataFilter,
    StateFilter,
    TypeFilter,
    filtered_handler,
)
from app.store.tg_api.dataclasses import CallbackTG


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
                text=consts.YOU_APPLY_TO_READY,
            )
            return

        elif len(active_connected_user_ids) >= MAX_PLAYERS:
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_,
                text="Набралось достаточное кол-ство человек",
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

        mess = await self.app.store.tg_api.send_message(
            chat_id=chat_id,
            text=PLAYER_JOINED.format(username=callback.from_.username),
        )
        await self.add_message_in_unnecessary_messages(
            chat_id=chat_id, message_id=mess.message_id
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
            if len(dict_idtg_to_players) < MIN_PLAYERS:
                await self.app.store.tg_api.answer_callback_query(
                    callback_query_id=callback.id_,
                    text=consts.LESS_MIN_PLAYERS,
                )
                return

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

            mess = await self.app.store.tg_api.send_message(
                chat_id=chat_id,
                text=consts.PLAYER_EXIT.format(
                    username=callback.from_.username
                ),
            )
            await self.add_message_in_unnecessary_messages(
                chat_id=chat_id, message_id=mess.message_id
            )
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=callback.id_, text=consts.YOU_EXIT_GAME
            )
