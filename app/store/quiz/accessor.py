from collections.abc import Iterable, Sequence

from sqlalchemy import select

from app.base.base_accessor import BaseAccessor
from app.quiz.models import (
    AnswerModel,
    QuestionModel,
    ThemeModel,
)


class QuizAccessor(BaseAccessor):
    async def create_theme(self, title: str) -> ThemeModel:
        async with await self.app.database.get_session() as session:
            new_theme = ThemeModel(title=title)
            session.add(new_theme)
            await session.commit()
        return new_theme

    async def get_theme_by_title(self, title: str) -> ThemeModel | None:
        async with await self.app.database.get_session() as session:
            stmt = select(ThemeModel).where(ThemeModel.title == title)
            result = await session.execute(stmt)
        return result.scalars().first()

    async def get_theme_by_id(self, id_: int) -> ThemeModel | None:
        async with await self.app.database.get_session() as session:
            stmt = select(ThemeModel).where(ThemeModel.id == id_)
            result = await session.execute(stmt)
        return result.scalars().first()

    async def list_themes(self) -> Sequence[ThemeModel]:
        async with await self.app.database.get_session() as session:
            stmt = select(ThemeModel)
            result = await session.execute(stmt)
        return result.scalars().all()

    async def create_question(
        self, title: str, theme_id: int, answers: Iterable[AnswerModel]
    ) -> QuestionModel:

        async with await self.app.database.get_session() as session:
            new_question = QuestionModel(
                title=title,
                theme_id=theme_id,
                answers=answers
            )
            session.add(new_question)
            await session.commit()
        return new_question

    async def get_question_by_title(
            self, title: str
    ) -> QuestionModel | None:
        async with await self.app.database.get_session() as session:
            stmt = select(QuestionModel).where(
                QuestionModel.title == title
            )
            result = await session.execute(stmt)
        return result.scalars().first()

    async def list_questions(
        self, theme_id: int | None = None
    ) -> Sequence[QuestionModel]:
        async with await self.app.database.get_session() as session:
            if theme_id is not None:
                stmt = select(QuestionModel).where(
                    QuestionModel.theme_id == theme_id
                )
            else:
                stmt = select(QuestionModel)
            result = await session.execute(stmt)
        return result.scalars().all()
