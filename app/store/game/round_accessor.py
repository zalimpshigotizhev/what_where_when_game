from sqlalchemy import select

from app.base.base_accessor import BaseAccessor
from app.bot.game.models import RoundModel


class RoundAccessor(BaseAccessor):
    async def create_round(
        self,
        session_id: int,
        question_id: int,
        is_active: bool = True,
        answer_player_id: int | None = None,
        is_correct_answer: bool | None = None,
    ) -> RoundModel:
        async with await self.app.database.get_session() as session:
            new_round = RoundModel(
                session_id=session_id,
                question_id=question_id,
                is_active=is_active,
                answer_player_id=answer_player_id,
                is_correct_answer=is_correct_answer,
            )
            session.add(new_round)
            await session.commit()
            return new_round

    async def set_answer_player_id(
        self,
        session_id: int,
        answer_player_id: int,
    ) -> RoundModel | None:
        async with await self.app.database.get_session() as session:
            stmt = select(RoundModel).where(
                RoundModel.session_id == session_id,
                RoundModel.is_active.is_(True),
            )
            result = await session.execute(stmt)
            exist_round: RoundModel = result.unique().scalar_one_or_none()
            exist_round.answer_player_id = answer_player_id
            await session.commit()
            return exist_round

    async def set_column_is_active_to_false(
        self,
        session_id: int,
    ) -> RoundModel | None:
        async with await self.app.database.get_session() as session:
            stmt = select(RoundModel).where(
                RoundModel.session_id == session_id,
                RoundModel.is_active.is_(True),
            )
            result = await session.execute(stmt)
            exist_round: RoundModel = result.unique().scalar_one_or_none()
            exist_round.is_active = False
            await session.commit()
            return exist_round

    async def set_column_is_correct_answer(
        self,
        new_is_correct_answer: bool,
        session_id: int | None = None,
        round_id: int | None = None,
    ) -> RoundModel | None:
        if session_id is None and round_id is None:
            return None

        async with await self.app.database.get_session() as session:
            if round_id is not None:
                stmt = select(RoundModel).where(
                    RoundModel.id == round_id,
                )
            else:
                stmt = select(RoundModel).where(
                    RoundModel.session_id == session_id,
                    RoundModel.is_active.is_(True),
                )
            result = await session.execute(stmt)
            exist_round: RoundModel = result.unique().scalar_one_or_none()
            exist_round.is_correct_answer = new_is_correct_answer
            await session.commit()
            return exist_round

    async def set_column_give_answer_by_player(
        self, session_id: int, answer_by_player
    ) -> RoundModel | None:
        async with await self.app.database.get_session() as session:
            stmt = select(RoundModel).where(
                RoundModel.session_id == session_id,
                RoundModel.is_active.is_(True),
            )
            result = await session.execute(stmt)
            exist_round: RoundModel = result.unique().scalar_one_or_none()
            exist_round.give_answer_by_player = answer_by_player
            await session.commit()
            return exist_round
