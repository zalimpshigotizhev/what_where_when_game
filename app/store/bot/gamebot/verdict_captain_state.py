from app.bot.game.models import GameState
from app.store.bot import consts
from app.store.bot.gamebot.base import BotBase
from app.store.bot.utils import StateFilter, TypeFilter, filtered_handler
from app.store.tg_api.dataclasses import MessageTG


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
                    self.app.store.timer_manager.start_timer(
                        chat_id=chat_id,
                        timeout=consts.WAIT_ANSWER_TIMEOUT,
                        callback=self.is_answer_false,
                        timer_type="30_second_for_answer",
                        # kwargs
                        current_chat_id=chat_id,
                        session_id=curr_sess.id,
                        text="*Игрок долго не решался что ответить.* \n"
                        "Вопрос засчитывается неверным.\n"
                        "Готовы к следующему вопросу?",
                    )
                    return
                mess = await self.app.store.tg_api.send_message(
                    chat_id=chat_id, text=consts.WARNING_CAP_DONT_EXIST_PLAYER
                )
                await self.add_message_in_unnecessary_messages(
                    chat_id=chat_id, message_id=mess.message_id
                )
