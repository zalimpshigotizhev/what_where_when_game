from collections.abc import Iterable, Sequence

from sqlalchemy import select

from app.base.base_accessor import BaseAccessor
from app.quiz.models import (
    AnswerMixin,
    QuestionMixin,
    ThemeMixin,
)


class QuizAccessor(BaseAccessor):
    async def create_theme(self, title: str) -> ThemeMixin:
        async with await self.app.database.get_session() as session:
            new_theme = ThemeMixin(title=title)
            session.add(new_theme)
            await session.commit()
        return new_theme


    async def get_theme_by_title(self, title: str) -> ThemeMixin | None:
        async with await self.app.database.get_session() as session:
            stmt = select(ThemeMixin).where(ThemeMixin.title == title)
            result = await session.execute(stmt)
            theme = result.scalars().first()
        return theme

    async def get_theme_by_id(self, id_: int) -> ThemeMixin | None:
        async with await self.app.database.get_session() as session:
            stmt = select(ThemeMixin).where(ThemeMixin.id == id_)
            result = await session.execute(stmt)
            theme = result.scalars().first()
        return theme

    async def list_themes(self) -> Sequence[ThemeMixin]:
        async with await self.app.database.get_session() as session:
            stmt = select(ThemeMixin)
            result = await session.execute(stmt)
            themes = result.scalars().all()
        return themes

    async def create_question(
        self, title: str, theme_id: int, answers: Iterable[AnswerMixin]
    ) -> QuestionMixin:

        async with await self.app.database.get_session() as session:
            new_question = QuestionMixin(
                title=title,
                theme_id=theme_id,
                answers=answers
            )
            session.add(new_question)
            await session.commit()
        return new_question

    async def get_question_by_title(self, title: str) -> QuestionMixin | None:
        async with await self.app.database.get_session() as session:
            stmt = select(QuestionMixin).where(QuestionMixin.title == title)
            result = await session.execute(stmt)
            theme = result.scalars().first()
        return theme

    async def list_questions(
        self, theme_id: int | None = None
    ) -> Sequence[QuestionMixin]:
        async with await self.app.database.get_session() as session:
            if theme_id is not None:
                stmt = select(QuestionMixin).where(QuestionMixin.theme_id == theme_id)
            else:
                stmt = select(QuestionMixin)
            result = await session.execute(stmt)
            themes = result.scalars().all()
        return themes
