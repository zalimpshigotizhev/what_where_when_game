from unittest.mock import AsyncMock, call

import pytest

from app.bot.game.models import GameState, PlayerModel, StatusSession
from app.bot.user.models import UserModel
from app.store.bot import consts
from app.store.bot.keyboards import are_ready_keyboard


class TestBotBase:
    """Тесты для базового класса BotBase"""

    @pytest.mark.asyncio
    async def test_initialization(self, bot_base, mock_app):
        """Тест инициализации BotBase"""
        assert bot_base.app == mock_app
        assert bot_base.handlers is not None

        assert bot_base.game_store == bot_base.app.store.game_session

    @pytest.mark.asyncio
    async def test_add_message_in_unnecessary_messages(
        self, bot_base, mock_app
    ):
        """Тест добавления сообщения в список для удаления"""
        chat_id = 123
        message_id = 456

        # Настраиваем мок FSM
        mock_app.store.fsm.get_data_by_csv.return_value = {}

        await bot_base.add_message_in_unnecessary_messages(chat_id, message_id)

        # Проверяем вызовы
        mock_app.store.fsm.get_data_by_csv.assert_called_once_with(chat_id)
        mock_app.store.fsm.update_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_deleted_unnecessary_messages(self, bot_base, mock_app):
        """Тест удаление списка сообщений для удаления"""
        chat_id = 123
        unnecessary_messages = [
            412,
        ]

        mock_app.store.fsm.get_data_by_csv.return_value = {
            "unnecessary_messages": unnecessary_messages,
            "other_data": "some_value",
        }

        await bot_base.deleted_unnecessary_messages(chat_id)

        # Проверяем вызовы
        tg_api = mock_app.store.tg_api
        mock_app.store.fsm.get_data_by_csv.assert_called_once_with(chat_id)
        tg_api.delete_messages.assert_called_once_with(
            chat_id, unnecessary_messages
        )
        mock_app.store.fsm.update_data.assert_called_once()

        expected_data = {"unnecessary_messages": [], "other_data": "some_value"}
        mock_app.store.fsm.update_data.assert_called_once_with(
            chat_id=chat_id, new_data=expected_data
        )

    @pytest.mark.asyncio
    async def test_cancel_game(self, bot_base, mock_app):
        """Тест на отмену игры
        Проверяется
        - что удаляется список 'ненужных сообщений'
        - что обновляется переданный аргументом статус
        - что отправляется сообщение через TGApi
        - что очищаются все таймеры
        """
        chat_id = 123
        session_id = 12
        new_status = StatusSession.COMPLETED
        text = (
            "Вы доказали, что вы настоящая команда. Когда снова захотите "
            "интеллектуально посоревноваться - я буду на месте 🦉"
        )

        bot_base.deleted_unnecessary_messages = AsyncMock()

        await bot_base.cancel_game(
            current_chat_id=chat_id,
            session_id=session_id,
            new_status=new_status,
            text=text,
        )

        bot_base.deleted_unnecessary_messages.assert_called_once_with(
            chat_id=chat_id
        )
        bot_base.game_store.set_status.assert_called_once_with(
            session_id=session_id, new_status=new_status
        )
        bot_base.app.store.tg_api.send_message.assert_called_once_with(
            chat_id=chat_id, text=text
        )
        bot_base.app.store.timer_manager.clean_timers.assert_called_once_with(
            chat_id=chat_id
        )

    @pytest.mark.asyncio
    async def test_ask_question_dont_exist_session(
        self, bot_base, mock_app, session_id, chat_id
    ):
        """Проверяем что функция возвращает None или конкретное значение
        при отсутствии сессии.
        """
        bot_base.deleted_unnecessary_messages = AsyncMock()
        bot_base.game_store.get_active_session_by_chat_id.return_value = None

        await bot_base.ask_question(
            current_chat_id=chat_id,
            session_id=session_id,
        )

        bot_base.game_store.get_active_session_by_chat_id.assert_called_once_with(
            chat_id=chat_id, inload_players=True
        )
        bot_base.app.store.tg_api.send_message.assert_called_once_with(
            chat_id=chat_id,
            text="*У вас нет активной игровой сессии.*\n" "Начните её /start",
        )
        bot_base.app.logger.error.assert_called_once_with(
            "Эта игра прекращена или в ожидании"
        )
        # Не вызываются
        bot_base.app.store.fsm.set_state.assert_not_called()
        bot_base.app.store.quizzes.random_question.assert_not_called()
        bot_base.round_store.create_round.assert_not_called()
        bot_base.app.store.timer_manager.start_timer.assert_not_called()

    @pytest.mark.asyncio
    async def test_ask_question_exclude_players(
        self, bot_base, mock_app, session_game, chat_id, session_id
    ):
        """Проверяем что функция отсекает всех,
        кто не был готов к вопросу
        """
        bot_base.deleted_unnecessary_messages = AsyncMock()
        expected_calls = [
            call(id_tg=43435343, session_id=session_id, new_active=False),
            call(id_tg=2323422, session_id=session_id, new_active=False),
            call(id_tg=12341312, session_id=session_id, new_active=False),
        ]
        players = [
            PlayerModel(
                session_id=session_id,
                is_active=True,
                is_ready=True,
                is_captain=True,
                user=UserModel(username_tg="zalimon", id_tg=1234123),
            ),
            PlayerModel(
                session_id=session_id,
                is_active=True,
                is_ready=True,
                is_captain=False,
                user=UserModel(username_tg="zalimoka", id_tg=1112222333),
            ),
            PlayerModel(
                session_id=session_id,
                is_active=True,
                is_ready=True,
                is_captain=False,
                user=UserModel(username_tg="bots", id_tg=34567777),
            ),
            PlayerModel(
                session_id=session_id,
                is_active=True,
                is_ready=False,
                is_captain=False,
                user=UserModel(username_tg="zalik", id_tg=43435343),
            ),
            PlayerModel(
                session_id=session_id,
                is_active=True,
                is_ready=False,
                is_captain=False,
                user=UserModel(username_tg="zalimoshka", id_tg=2323422),
            ),
            PlayerModel(
                session_id=session_id,
                is_active=False,
                is_ready=True,
                is_captain=False,
                user=UserModel(username_tg="zalimchik", id_tg=12341312),
            ),
        ]
        game_store = bot_base.game_store
        session_game.players = players
        game_store.get_active_session_by_chat_id.return_value = session_game

        await bot_base.ask_question(
            current_chat_id=chat_id,
            session_id=session_id,
        )

        game_store.get_active_session_by_chat_id.assert_called_once_with(
            chat_id=chat_id, inload_players=True
        )

        assert session_game.status == StatusSession.PROCESSING
        assert bot_base.player_store.set_player_is_active.call_count == 3
        bot_base.player_store.set_player_is_active.assert_has_calls(
            expected_calls
        )
        bot_base.app.store.fsm.set_state.assert_called_once_with(
            chat_id=chat_id, new_state=GameState.QUESTION_DISCUTION
        )
        bot_base.app.store.quizzes.random_question.assert_called()
        bot_base.round_store.create_round.assert_called()
        bot_base.game_store.set_current_round.assert_called()
        bot_base.app.store.tg_api.send_message.assert_called()
        bot_base.app.store.timer_manager.start_timer.assert_called_once_with(
            chat_id=chat_id,
            timeout=consts.QUESTION_DISCUTION_TIMEOUT,
            callback=bot_base.verdict_captain,
            timer_type="1_minute_question_discution",
            # kwargs
            current_chat_id=chat_id,
            session_id=session_id,
        )

    @pytest.mark.asyncio
    async def test_ask_question_exclude_captain(
        self,
        bot_base,
        mock_app,
        session_game,
        chat_id,
        session_id,
        full_players,
        player1,
    ):
        """Проверяем что функция отсекает всех,
        кто не был готов к вопросу.
        В случае если выходит капитан
        """
        bot_base.deleted_unnecessary_messages = AsyncMock()
        bot_base.cancel_game = AsyncMock()
        game_store = bot_base.game_store
        session_game.players = full_players
        game_store.get_active_session_by_chat_id.return_value = session_game

        player1.is_ready = False

        await bot_base.ask_question(
            current_chat_id=chat_id,
            session_id=session_id,
        )

        game_store.get_active_session_by_chat_id.assert_called_once_with(
            chat_id=chat_id, inload_players=True
        )

        assert session_game.status == StatusSession.PROCESSING
        bot_base.cancel_game.assert_called_once_with(
            current_chat_id=chat_id, session_id=session_id
        )

        bot_base.app.store.quizzes.random_question.assert_not_called()
        bot_base.round_store.create_round.assert_not_called()
        bot_base.game_store.set_current_round.assert_not_called()
        bot_base.app.store.tg_api.send_message.assert_not_called()
        bot_base.app.store.timer_manager.start_timer.assert_not_called()

    @pytest.mark.asyncio
    async def test_ask_question_enough_players(
        self, bot_base, mock_app, session_game, chat_id, session_id, player1
    ):
        """Проверяем как себя ведет функция,
        если не хватает участников до MIN_PLAYERS.
        """
        bot_base.deleted_unnecessary_messages = AsyncMock()
        bot_base.cancel_game = AsyncMock()
        session_game.players = [player1]
        game_store = bot_base.game_store
        game_store.get_active_session_by_chat_id.return_value = session_game

        await bot_base.ask_question(
            current_chat_id=chat_id,
            session_id=session_id,
        )

        bot_base.game_store.get_active_session_by_chat_id.assert_called_once_with(
            chat_id=chat_id, inload_players=True
        )

        assert session_game.status == StatusSession.PROCESSING

        bot_base.cancel_game.assert_called_once_with(
            current_chat_id=chat_id,
            session_id=session_id,
            text=consts.ENOUGH_PLAYERS,
        )

        bot_base.app.store.quizzes.random_question.assert_not_called()
        bot_base.round_store.create_round.assert_not_called()
        bot_base.game_store.set_current_round.assert_not_called()
        bot_base.app.store.tg_api.send_message.assert_not_called()
        bot_base.app.store.timer_manager.start_timer.assert_not_called()

    @pytest.mark.asyncio
    async def test_verdict_captain_dont_exist_sess(
        self, bot_base, mock_app, session_game
    ):
        """Тест на то, что задается вопрос капитану.
        Но сессии не существует
        """
        chat_id = 123
        session_id = 321

        bot_base.deleted_unnecessary_messages = AsyncMock()
        bot_base.game_store.get_active_session_by_chat_id.return_value = None

        await bot_base.verdict_captain(
            current_chat_id=chat_id,
            session_id=session_id,
        )

        bot_base.game_store.get_active_session_by_chat_id.assert_called_once_with(
            chat_id=chat_id, inload_players=True
        )
        bot_base.app.store.tg_api.send_message.assert_called_once_with(
            chat_id=chat_id,
            text="*У вас нет активной игровой сессии.*\n" "Начните её /start",
        )
        bot_base.app.logger.error.assert_called_once_with(
            "Эта игра прекращена или в ожидании"
        )
        # Не вызываются
        bot_base.app.store.fsm.set_state.assert_not_called()
        bot_base.app.store.timer_manager.start_timer.assert_not_called()

    @pytest.mark.asyncio
    async def test_verdict_captain(
        self,
        bot_base,
        mock_app,
        session_game,
        chat_id,
        session_id,
        full_players,
    ):
        """Тест на то, что задается вопрос капитану."""
        session_game.players = full_players
        game_store = bot_base.game_store
        players_for_answer = "\n".join(
            [f"· @{player.user.username_tg}" for player in session_game.players]
        )

        game_store.get_active_session_by_chat_id.return_value = session_game

        await bot_base.verdict_captain(
            current_chat_id=chat_id,
            session_id=session_id,
        )

        bot_base.app.store.tg_api.send_message.assert_called_once_with(
            chat_id=chat_id,
            text=consts.MESSAGE_FOR_CAPTAIN.format(
                players_for_answer=players_for_answer
            ),
        )

        bot_base.app.store.fsm.set_state.assert_called_once_with(
            chat_id=chat_id, new_state=GameState.VERDICT_CAPTAIN
        )
        bot_base.app.store.timer_manager.start_timer.assert_called_once_with(
            chat_id=chat_id,
            timeout=consts.VERDICT_CAPTAIN_TIMEOUT,
            callback=bot_base.cancel_game,
            timer_type="2_minute_verdict_captain",
            # kwargs
            current_chat_id=chat_id,
            session_id=session_id,
            text="*Капитан долго не выбирал игрока.* \n" "Игра отменена.",
        )

    @pytest.mark.asyncio
    async def test_check_and_notify_score_bot_win(
        self, bot_base, mock_app, chat_id, session_id
    ):
        """Тест на то, что отображается score и отслеживается
        ботом прогресс игры.
        Тестовый случай когда боты победили
        """
        score = {
            "experts": 1,
            "bot": consts.MAX_SCORE,
            "total_rounds": 1 + consts.MAX_SCORE,
        }
        bot_base.game_store.gen_score.return_value = score
        bot_base.cancel_game = AsyncMock()
        is_continue = await bot_base.check_and_notify_score(
            session_id=session_id, chat_id=chat_id
        )

        assert is_continue is False

        bot_base.game_store.gen_score.assert_called_once_with(
            session_id=session_id
        )
        bot_base.app.store.tg_api.send_message.assert_called_with(
            chat_id=chat_id,
            text=consts.RUPOR_SCORE.format(
                experts=score.get("experts"), bot=score.get("bot")
            ),
        )

        bot_base.cancel_game.assert_called_once_with(
            session_id=session_id,
            current_chat_id=chat_id,
            text=consts.GAME_COMPLETED_FALSE,
            new_status=StatusSession.COMPLETED,
        )

    @pytest.mark.asyncio
    async def test_check_and_notify_score_experts_win(
        self, bot_base, mock_app, chat_id, session_id
    ):
        """Тест на то, что отображается score и отслеживается
        ботом прогресс игры.
        Тестовый случай когда знатоки победили
        """
        score = {
            "experts": consts.MAX_SCORE,
            "bot": 3,
            "total_rounds": 3 + consts.MAX_SCORE,
        }
        bot_base.game_store.gen_score.return_value = score
        bot_base.cancel_game = AsyncMock()
        is_continue = await bot_base.check_and_notify_score(
            session_id=session_id, chat_id=chat_id
        )

        assert is_continue is False

        bot_base.game_store.gen_score.assert_called_once_with(
            session_id=session_id
        )
        bot_base.app.store.tg_api.send_message.assert_called_with(
            chat_id=chat_id,
            text=consts.RUPOR_SCORE.format(
                experts=score.get("experts"), bot=score.get("bot")
            ),
        )

        bot_base.cancel_game.assert_called_once_with(
            session_id=session_id,
            current_chat_id=chat_id,
            new_status=StatusSession.COMPLETED,
            text=consts.GAME_COMPLETED_TRUE,
        )

    @pytest.mark.asyncio
    async def test_check_and_notify_score_game_continuie(
        self, bot_base, mock_app, chat_id, session_id
    ):
        """Тест на то, что отображается score и отслеживается
        ботом прогресс игры.
        Тестовый случай когда знатоки победили
        """
        score = {
            "experts": consts.MAX_SCORE - 2,
            "bot": consts.MAX_SCORE - 2,
            "total_rounds": consts.MAX_SCORE - 4,
        }
        bot_base.game_store.gen_score.return_value = score
        bot_base.cancel_game = AsyncMock()
        is_continue = await bot_base.check_and_notify_score(
            session_id=session_id, chat_id=chat_id
        )

        assert is_continue is True

        bot_base.game_store.gen_score.assert_called_once_with(
            session_id=session_id
        )
        bot_base.app.store.tg_api.send_message.assert_called_with(
            chat_id=chat_id,
            text=consts.RUPOR_SCORE.format(
                experts=score.get("experts"), bot=score.get("bot")
            ),
        )

        bot_base.cancel_game.assert_not_called()

    @pytest.mark.asyncio
    async def test_is_answer_false(
        self, bot_base, mock_app, session_game, chat_id, session_id
    ):
        """Тест на то, что ответ неправильный (по разным причинам)."""
        text = "К сожалению вот так вот"
        bot_base.check_and_notify_score = AsyncMock()
        bot_base.add_message_in_unnecessary_messages = AsyncMock()
        await bot_base.is_answer_false(
            session_id=session_id, current_chat_id=chat_id, text=text
        )
        bot_base.player_store.set_all_players_is_ready_false.assert_called_with(
            session_id=session_id
        )
        bot_base.round_store.set_column_is_correct_answer.assert_called_with(
            session_id=session_id, new_is_correct_answer=False
        )
        bot_base.round_store.set_column_is_active_to_false.assert_called_with(
            session_id=session_id
        )
        bot_base.check_and_notify_score.assert_called_with(
            session_id=session_id, chat_id=chat_id
        )
        bot_base.app.store.tg_api.send_message.assert_called_with(
            chat_id=chat_id,
            text=text,
            reply_markup=are_ready_keyboard,
        )
        bot_base.add_message_in_unnecessary_messages.assert_called()
        bot_base.app.store.fsm.set_state.assert_called_with(
            chat_id=chat_id,
            new_state=GameState.ARE_READY_NEXT_ROUND_PLAYERS,
        )

    @pytest.mark.asyncio
    async def test_is_next_quest(self, bot_base, mock_app, chat_id, session_id):
        """Тест на то, что появляется вопрос о готовности
        к след вопросу.
        """
        text = "К след готовы?"
        bot_base.add_message_in_unnecessary_messages = AsyncMock()

        await bot_base.next_quest(
            text=text, chat_id=chat_id, session_id=session_id
        )

        bot_base.player_store.set_all_players_is_ready_false.assert_called_with(
            session_id=session_id
        )

        bot_base.app.store.tg_api.send_message.assert_called_with(
            chat_id=chat_id,
            text=text,
            reply_markup=are_ready_keyboard,
        )
        bot_base.add_message_in_unnecessary_messages.assert_called()

        bot_base.app.store.fsm.set_state.assert_called_with(
            chat_id=chat_id, new_state=GameState.ARE_READY_NEXT_ROUND_PLAYERS
        )

        bot_base.app.store.timer_manager.start_timer.assert_called_with(
            chat_id=chat_id,
            timeout=consts.ARE_READY_TIMEOUT,
            callback=bot_base.ask_question,
            timer_type="30_second_are_ready",
            # kwargs
            current_chat_id=chat_id,
            session_id=session_id,
        )
