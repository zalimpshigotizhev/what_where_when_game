import pytest
from sqlalchemy import select

from app.bot.game.models import RoundModel
from tests.utils import game_rounds_to_dict


class TestPlayerAccessor:
    async def test_table_exists(self, inspect_list_tables: list[str]):
        assert "rounds" in inspect_list_tables

    @pytest.mark.asyncio
    async def test_create_round(
        self,
        store,
        question,
        active_game_session,
        db_sessionmaker,
    ):
        new_round = await store.rounds.create_round(
            session_id=active_game_session.id,
            question_id=question.id,
            is_active=True,
            answer_player_id=None,
            is_correct_answer=None,
        )

        assert new_round is not None
        assert isinstance(new_round, RoundModel)

        async with db_sessionmaker() as sess:
            rounds = await sess.execute(select(RoundModel))
            rounds_list = rounds.unique().scalars()

        assert game_rounds_to_dict(rounds_list) == [
            {
                "id": new_round.id,
                "session_id": new_round.session_id,
                "is_active": new_round.is_active,
                "is_correct_answer": new_round.is_correct_answer,
                "question_id": new_round.question_id,
                "answer_player_id": new_round.answer_player_id,
            }
        ]

    @pytest.mark.asyncio
    async def test_set_answer_player_id(
        self,
        store,
        question,
        db_sessionmaker,
        active_round,
        active_player,
        active_game_session,
    ):
        assert active_round.answer_player_id is None

        await store.rounds.set_answer_player_id(
            session_id=active_game_session.id, answer_player_id=active_player.id
        )
        curr_sess = await store.game_session.get_session_by_id(
            session_id=active_game_session.id,
        )
        curr_round = curr_sess.current_round

        assert curr_sess is not None
        assert curr_round.answer_player_id == active_player.id

    @pytest.mark.asyncio
    async def test_set_is_active_to_false(
        self,
        store,
        question,
        db_sessionmaker,
        active_round,
        active_player,
        active_game_session,
    ):
        assert active_round.is_active is True

        await store.rounds.set_is_active_to_false(
            session_id=active_game_session.id,
        )

        async with db_sessionmaker() as sess:
            res = await sess.execute(
                select(RoundModel).where(RoundModel.id == active_round.id)
            )
            curr_round = res.unique().scalars().one_or_none()

        assert curr_round is not None
        assert curr_round.is_active is False

    @pytest.mark.asyncio
    async def test_set_is_correct_answer(
        self,
        store,
        question,
        db_sessionmaker,
        active_round,
        active_player,
        active_game_session,
    ):
        assert active_round.is_correct_answer is None

        await store.rounds.set_is_correct_answer(
            session_id=active_game_session.id, new_is_correct_answer=False
        )

        async with db_sessionmaker() as sess:
            res = await sess.execute(
                select(RoundModel).where(RoundModel.id == active_round.id)
            )
            curr_round = res.unique().scalars().one_or_none()

        assert curr_round is not None
        assert curr_round.is_correct_answer is False
