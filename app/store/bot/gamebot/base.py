import asyncio
from typing import TYPE_CHECKING

from app.bot.game.models import (
    PlayerModel,
    RoundModel, StatusSession, GameState,
)
from app.quiz.models import QuestionModel
from app.store.bot import consts
from app.store.bot.keyboards import (
    are_ready_keyboard,
)

if TYPE_CHECKING:
    from app.web.app import Application
    from app.store import GameSessionAccessor



class GameProcessedError(Exception):
    pass


class BotBase:
    def __init__(self, app: "Application"):
        self.app = app
        self.handlers: list | None = None
        self._add_handlers_in_list()

    @property
    def round_store(self):
        return self.app.store.rounds

    @property
    def game_store(self) -> 'GameSessionAccessor':
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
        curr_sess = await self.game_store.get_active_session_by_chat_id(
            chat_id=current_chat_id, inload_players=True
        )
        if not curr_sess or curr_sess.status != StatusSession.PROCESSING:
            await self.app.store.tg_api.send_message(
                chat_id=current_chat_id,
                text=("*У вас нет активной игровой сессии.*\n"
                     "Начните её /start")
            )
            self.app.logger.error("Эта игра прекращена или в ожидании")
            return

        # Уничтожить всех кто не был готов к вопросу
        players: list[PlayerModel] = curr_sess.players
        players_is_active_is_ready = []

        for player in players:
            if player.is_active is False or player.is_ready is False:
                if player.is_captain:
                    await self.cancel_game(
                        current_chat_id=current_chat_id, session_id=curr_sess.id
                    )
                    return
                await self.player_store.set_player_is_active(
                    session_id=curr_sess.id,
                    id_tg=player.user.id_tg,
                    new_active=False,
                )
            else:
                players_is_active_is_ready.append(player)

        if len(players_is_active_is_ready) < consts.MIN_PLAYERS:
            await self.cancel_game(
                current_chat_id=current_chat_id, session_id=curr_sess.id,
                text=consts.ENOUGH_PLAYERS
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
            chat_id=current_chat_id,
            text=consts.RUPOR_QUEST.format(
                theme=rand_question.theme.title, question=rand_question.title
            ),
        )

        self.app.store.timer_manager.start_timer(
            chat_id=current_chat_id,
            timeout=consts.QUESTION_DISCUTION_TIMEOUT,
            callback=self.verdict_captain,
            timer_type="1_minute_question_discution",
            # kwargs
            current_chat_id=current_chat_id,
            session_id=session_id,
        )

    async def verdict_captain(
            self,
            current_chat_id: int,
            session_id: int,
    ):
        """Переходная функция для опроса капитана."""
        curr_sess = await self.game_store.get_active_session_by_chat_id(
            chat_id=current_chat_id, inload_players=True
        )
        if curr_sess is None:
            await self.app.store.tg_api.send_message(
                chat_id=current_chat_id,
                text=("*У вас нет активной игровой сессии.*\n"
                     "Начните её /start")
            )
            self.app.logger.error("Эта игра прекращена или в ожидании")
            return

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
            timeout=consts.VERDICT_CAPTAIN_TIMEOUT,
            callback=self.cancel_game,
            timer_type="2_minute_verdict_captain",
            # kwargs
            current_chat_id=current_chat_id,
            session_id=curr_sess.id,
            text="*Капитан долго не выбирал игрока.* \n" "Игра отменена.",
        )

    async def check_and_notify_score(
        self,
        session_id: int,
        chat_id: int,
    ) -> bool:
        score = await self.game_store.gen_score(session_id=session_id)

        await self.app.store.tg_api.send_message(
            chat_id=chat_id,
            text=consts.RUPOR_SCORE.format(
                experts=score.get("experts"), bot=score.get("bot")
            ),
        )

        if score.get("experts") == consts.MAX_SCORE:
            await self.cancel_game(
                session_id=session_id,
                current_chat_id=chat_id,
                new_status=StatusSession.COMPLETED,
                text=consts.GAME_COMPLETED_TRUE,
            )
            return False

        if score.get("bot") == consts.MAX_SCORE:
            await self.cancel_game(
                session_id=session_id,
                current_chat_id=chat_id,
                text=consts.GAME_COMPLETED_FALSE,
                new_status=StatusSession.COMPLETED,
            )
            return False

        return True

    async def is_answer_false(
        self, session_id: int, current_chat_id: int, text: str
    ):
        await self.player_store.set_all_players_is_ready_false(
            session_id=session_id
        )

        await self.round_store.set_is_correct_answer(
            session_id=session_id, new_is_correct_answer=False
        )
        await self.round_store.set_is_active_to_false(session_id=session_id)
        await self.check_and_notify_score(
            session_id=session_id, chat_id=current_chat_id
        )

        mess = await self.app.store.tg_api.send_message(
            chat_id=current_chat_id,
            text=text,
            reply_markup=are_ready_keyboard,
        )
        await self.add_message_in_unnecessary_messages(
            chat_id=current_chat_id, message_id=mess.message_id
        )

        await self.app.store.fsm.set_state(
            chat_id=current_chat_id,
            new_state=GameState.ARE_READY_NEXT_ROUND_PLAYERS,
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
            timeout=consts.ARE_READY_TIMEOUT,
            callback=self.ask_question,
            timer_type="30_second_are_ready",
            # kwargs
            current_chat_id=chat_id,
            session_id=session_id,
        )
