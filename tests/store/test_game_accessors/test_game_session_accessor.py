import pytest
from sqlalchemy import select

from app.bot.game.models import (
    GameState,
    RoundModel,
    SessionModel,
    StateModel,
    StatusSession,
)
from app.quiz.models import AnswerModel, QuestionModel, ThemeModel
from tests.utils import (
    game_session_to_dict,
    game_sessions_to_dict,
    game_states_to_dict,
)


class TestGameSessionAccessor:
    async def test_table_exists(self, inspect_list_tables: list[str]):
        assert "sessions" in inspect_list_tables
        assert "states" in inspect_list_tables

    @pytest.mark.asyncio
    async def test_create_session(
        self,
        store,
        session_id,
        chat_id,
        db_sessionmaker,
    ):
        new_game_session = await store.game_session.create_session(
            chat_id=chat_id, status=StatusSession.PENDING
        )

        assert new_game_session is not None
        assert isinstance(new_game_session, SessionModel)

        async with db_sessionmaker() as sess:
            sessions = await sess.execute(select(SessionModel))
            states = await sess.execute(select(StateModel))

            sessions_list = sessions.unique().scalars()
            states_list = states.unique().scalars()

        assert game_sessions_to_dict(sessions_list) == [
            {
                "id": 1,
                "chat_id": chat_id,
                "status": StatusSession.PENDING,
                "current_round_id": None,
            }
        ]
        assert game_states_to_dict(states_list) == [
            {
                "id": 1,
                "session_id": 1,
                "current_state": GameState.INACTIVE,
                "data": {},
            }
        ]

    @pytest.mark.asyncio
    async def test_get_session_by_id(
        self, store, session_id, chat_id, db_sessionmaker, active_game_session
    ):
        game_session = await store.game_session.get_session_by_id(
            session_id=active_game_session.id
        )

        assert game_session is not None
        assert game_session_to_dict(game_session) == {
            "id": 1,
            "chat_id": chat_id,
            "status": StatusSession.PROCESSING,
            "current_round_id": None,
        }

    @pytest.mark.asyncio
    async def test_get_active_session_by_chat_id(
        self, store, db_sessionmaker, active_game_session
    ):
        game_session = await store.game_session.get_active_session_by_chat_id(
            chat_id=active_game_session.chat_id
        )

        assert game_session is not None
        assert game_session_to_dict(game_session) == {
            "id": 1,
            "chat_id": active_game_session.chat_id,
            "status": StatusSession.PROCESSING,
            "current_round_id": None,
        }

    @pytest.mark.asyncio
    async def test_get_active_sessions(
        self,
        store,
        active_game_session,
        db_sessionmaker,
    ):
        game_sessions = await store.game_session.get_active_sessions()

        assert game_sessions is not None
        assert len(game_sessions) != 0
        assert game_sessions_to_dict(game_sessions) == [
            {
                "id": 1,
                "chat_id": active_game_session.chat_id,
                "status": StatusSession.PROCESSING,
                "current_round_id": None,
            }
        ]

    @pytest.mark.asyncio
    async def test_set_status(
        self,
        store,
        active_game_session,
        db_sessionmaker,
    ):
        current_status = active_game_session.status
        new_status = StatusSession.COMPLETED

        assert active_game_session.status == current_status

        updated_session = await store.game_session.set_status(
            session_id=active_game_session.id, new_status=new_status
        )
        assert updated_session.status == new_status

    @pytest.mark.asyncio
    async def test_set_current_round(
        self,
        store,
        chat_id,
        active_game_session,
        db_sessionmaker,
    ):
        async with db_sessionmaker() as sess:
            new_round = RoundModel(
                session_id=active_game_session.id,
                is_active=True,
                is_correct_answer=True,
                question=QuestionModel(
                    title="QuestionTitlte",
                    theme=ThemeModel(title="ThemeTitle"),
                    true_answer=AnswerModel(
                        title="AnswerTitle", description="Description"
                    ),
                ),
            )
            sess.add(new_round)
            await sess.commit()
            await sess.refresh(new_round)

        assert active_game_session.current_round_id is None

        await store.game_session.set_current_round(
            session_id=active_game_session.id, round_id=new_round.id
        )

        corr_session = await store.game_session.get_session_by_id(
            session_id=active_game_session.id
        )

        assert corr_session.current_round_id is not None
        assert corr_session.current_round_id == new_round.id

    @pytest.mark.asyncio
    async def test_gen_score(
        self, store, chat_id, db_sessionmaker, active_game_session
    ):
        scores = await store.game_session.gen_score(
            session_id=active_game_session.id,
        )
        assert scores == {
            "experts": 0,
            "bot": 0,
            "total_rounds": 0,
        }

    @pytest.mark.asyncio
    async def test_get_completed_sessions(
        self, store, chat_id, db_sessionmaker, active_game_session
    ):
        await store.game_session.set_status(
            session_id=active_game_session.id,
            new_status=StatusSession.COMPLETED,
        )
        completed_sessions = await store.game_session.get_completed_sessions(
            chat_id=active_game_session.chat_id
        )

        assert game_sessions_to_dict(completed_sessions) == [
            {
                "id": 1,
                "chat_id": active_game_session.id,
                "status": StatusSession.COMPLETED,
                "current_round_id": None,
            }
        ]
