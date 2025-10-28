import asyncio

from app.bot.game.models import GameState, PlayerModel, RoundModel
from app.quiz.models import QuestionModel
from app.store.bot import consts
from app.store.bot.gamebot.base import BotBase
from app.store.bot.keyboards import (
    are_ready_keyboard,
    are_ready_keyboard_or_dispute_answer,
    yes_or_no_for_dispute,
)
from app.store.bot.utils import (
    CallbackDataFilter,
    StateFilter,
    TypeFilter,
    escape_markdown,
    filtered_handler,
)
from app.store.rabbit.dataclasses import CallbackTG, MessageTG


class WaitAnswer(BotBase):
    @filtered_handler(TypeFilter(MessageTG), StateFilter(GameState.WAIT_ANSWER))
    async def handle_wait_answer(
        self, message: MessageTG, context: GameState | None
    ) -> None:
        """Обработка ответа в состоянии ожидания.

        В этом состоянии мы должны получить
        ответ от выбранного капитаном игрока.
        Если получаем сообщение от другого участника -
        бот присваивает балл себе.
        Если ответ от нужного игрока и он корректный -
        балл команде знатоков.
        В любом случае раунд завершается.
        """
        chat_id = message.chat.id_
        curr_sess = await self.game_store.get_active_session_by_chat_id(
            chat_id=chat_id,
        )
        current_round: RoundModel = curr_sess.current_round
        question: QuestionModel = current_round.question
        player: PlayerModel = current_round.answer_player
        self.app.store.timer_manager.cancel_timer(
            chat_id=chat_id, timer_type="30_second_for_answer"
        )
        if player.user.id_tg != message.from_.id_:
            await self.is_answer_false(
                session_id=curr_sess.id,
                current_chat_id=chat_id,
                text=f"Должен был ответить - @{player.user.username_tg}\n"
                f"А ответил @{message.from_.username}\n"
                f"*Ответ засчитан как неправильный! Будьте внимательны*",
            )
            return

        is_correct_answer = question.is_answer_is_true(message.text)
        if question.true_answer.description:
            await self.app.store.tg_api.send_message(
                chat_id=chat_id,
                text=consts.DESCRIPTION_ANSWER.format(
                    description=escape_markdown(
                        question.true_answer.description
                    )
                ),
                parse_mode="MarkdownV2",
            )
            await asyncio.sleep(3)

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
        await self.round_store.set_column_give_answer_by_player(
            session_id=curr_sess.id, answer_by_player=message.text
        )
        await self.round_store.set_column_is_correct_answer(
            session_id=curr_sess.id, new_is_correct_answer=is_correct_answer
        )
        await self.round_store.set_column_is_active_to_false(
            session_id=curr_sess.id
        )

        should_continue = await self.check_and_notify_score(
            session_id=curr_sess.id, chat_id=chat_id
        )
        if should_continue:
            if is_correct_answer:
                keyboard = are_ready_keyboard
            else:
                keyboard = are_ready_keyboard_or_dispute_answer

            await self.next_quest(
                text=consts.ARE_YOU_READY_NEXT_QUEST,
                chat_id=chat_id,
                session_id=curr_sess.id,
                keyboard=keyboard,
            )

    @filtered_handler(
        TypeFilter(CallbackTG),
        CallbackDataFilter("disput_answer"),
    )
    async def handle_disput_answer(
        self, callback: CallbackTG, context: GameState | None
    ) -> None:
        chat_id = callback.chat.id_
        curr_sess = await self.game_store.get_active_session_by_chat_id(
            chat_id=chat_id,
            inload_players=True,
        )
        for player in curr_sess.players:
            if player.user.id_tg == callback.from_.id_:
                if player.is_captain:
                    await self.deleted_unnecessary_messages(chat_id=chat_id)
                    mess = await self.app.store.tg_api.send_message(
                        chat_id=chat_id,
                        text=consts.ARE_YOU_SURE_DISPUTE.format(
                            question=curr_sess.current_round.question.title,
                            player_answer=curr_sess.current_round.answer_player.user.username_tg,
                            give_answer=curr_sess.current_round.give_answer_by_player,
                            true_answer=curr_sess.current_round.question.true_answer.title,
                        ),
                        reply_markup=yes_or_no_for_dispute,
                    )
                    await self.add_message_in_unnecessary_messages(
                        chat_id=chat_id, message_id=mess.message_id
                    )
                    await self.app.store.fsm.set_state(
                        chat_id=chat_id, new_state=GameState.DISPUTE_ANSWER
                    )
                    self.app.store.timer_manager.cancel_timer(
                        chat_id=chat_id, timer_type="30_second_are_ready"
                    )
                else:
                    await self.app.store.tg_api.answer_callback_query(
                        callback_query_id=callback.id_,
                        text=consts.ONLY_CAPTAIN_FUNC,
                    )
            else:
                await self.app.store.tg_api.answer_callback_query(
                    callback_query_id=callback.id_,
                    text=consts.YOU_DONT_PLAYER,
                )

    @filtered_handler(
        TypeFilter(CallbackTG),
        CallbackDataFilter("yes_dispute"),
        StateFilter(GameState.DISPUTE_ANSWER),
    )
    async def handle_yes_dispute(
        self, callback: CallbackTG, context: GameState | None
    ) -> None:
        chat_id = callback.chat.id_
        curr_sess = await self.game_store.get_active_session_by_chat_id(
            chat_id=chat_id,
            inload_players=True,
        )
        for player in curr_sess.players:
            if player.user.id_tg == callback.from_.id_:
                if player.is_captain:
                    await self.deleted_unnecessary_messages(chat_id=chat_id)
                    await self.round_store.set_column_is_correct_answer(
                        round_id=curr_sess.current_round_id,
                        new_is_correct_answer=True,
                    )
                    should_continue = await self.check_and_notify_score(
                        session_id=curr_sess.id, chat_id=chat_id
                    )
                    if should_continue:
                        await self.next_quest(
                            text=consts.YOURE_SET_IS_ANSWER_TRUE,
                            chat_id=chat_id,
                            session_id=curr_sess.id,
                            keyboard=are_ready_keyboard,
                        )
                else:
                    await self.app.store.tg_api.answer_callback_query(
                        callback_query_id=callback.id_,
                        text=consts.ONLY_CAPTAIN_FUNC,
                    )
            else:
                await self.app.store.tg_api.answer_callback_query(
                    callback_query_id=callback.id_,
                    text=consts.YOU_DONT_PLAYER,
                )

    @filtered_handler(
        TypeFilter(CallbackTG),
        CallbackDataFilter("no_dispute"),
        StateFilter(GameState.DISPUTE_ANSWER),
    )
    async def handle_no_dispute(
        self, callback: CallbackTG, context: GameState | None
    ) -> None:
        chat_id = callback.chat.id_
        curr_sess = await self.game_store.get_active_session_by_chat_id(
            chat_id=chat_id,
            inload_players=True,
        )
        for player in curr_sess.players:
            if player.user.id_tg == callback.from_.id_:
                if player.is_captain:
                    await self.deleted_unnecessary_messages(chat_id=chat_id)

                    await self.next_quest(
                        text=consts.YOURE_SET_IS_ANSWER_TRUE,
                        chat_id=chat_id,
                        session_id=curr_sess.id,
                        keyboard=are_ready_keyboard,
                    )
                else:
                    await self.app.store.tg_api.answer_callback_query(
                        callback_query_id=callback.id_,
                        text=consts.ONLY_CAPTAIN_FUNC,
                    )
            else:
                await self.app.store.tg_api.answer_callback_query(
                    callback_query_id=callback.id_,
                    text=consts.YOU_DONT_PLAYER,
                )
