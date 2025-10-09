import asyncio

from app.bot.game.models import GameState
from app.store.bot import consts
from app.store.bot.gamebot.base import BotBase
from app.store.bot.utils import (
    CallbackDataFilter,
    StateFilter,
    TypeFilter,
    filtered_handler,
)
from app.store.tg_api.dataclasses import CallbackTG


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
        # TODO: Проверить добавляется ли дважды
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
