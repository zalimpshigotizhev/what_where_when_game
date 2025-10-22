import asyncio

from app.bot.game.models import GameState, PlayerModel, RoundModel
from app.quiz.models import QuestionModel
from app.store.bot import consts
from app.store.bot.gamebot.base import BotBase
from app.store.bot.utils import (
    StateFilter,
    TypeFilter,
    escape_markdown,
    filtered_handler,
)
from app.store.rabbit.dataclasses import MessageTG


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
        if is_correct_answer and question.true_answer.description:
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

        await self.round_store.set_is_correct_answer(
            session_id=curr_sess.id, new_is_correct_answer=is_correct_answer
        )
        await self.round_store.set_is_active_to_false(session_id=curr_sess.id)

        should_continue = await self.check_and_notify_score(
            session_id=curr_sess.id, chat_id=chat_id
        )
        if should_continue:
            await self.next_quest(
                text=consts.ARE_YOU_READY_NEXT_QUEST,
                chat_id=chat_id,
                session_id=curr_sess.id,
            )
