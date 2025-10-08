import re

from sqlalchemy import BigInteger, Column, ForeignKey, String
from sqlalchemy.orm import relationship

from app.bot.game.models import RoundModel  # noqa: F401
from app.store.database.sqlalchemy_base import BaseModel, TimedBaseMixin


class ThemeModel(TimedBaseMixin, BaseModel):
    __tablename__ = "themes"
    id = Column(BigInteger, primary_key=True, autoincrement=True, unique=True)
    title = Column(String, unique=True)
    questions = relationship(
        "QuestionModel", back_populates="theme", cascade="all, delete-orphan"
    )


class QuestionModel(TimedBaseMixin, BaseModel):
    __tablename__ = "questions"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(String, unique=True)
    theme_id = Column(
        BigInteger,
        ForeignKey("themes.id", ondelete="CASCADE"),
        nullable=False,
        unique=False,
    )

    theme = relationship(
        "ThemeModel", back_populates="questions", lazy="joined"
    )
    true_answer = relationship(
        "AnswerModel", uselist=False, backref="question", lazy="joined"
    )
    rounds = relationship("RoundModel", back_populates="question")

    def is_answer_is_true(self, answer: str) -> bool:
        normalized_input = re.sub(r"\s+", " ", answer.lower().strip())
        normalized_correct = re.sub(
            r"\s+", " ", self.true_answer.title.lower().strip()
        )
        return normalized_input == normalized_correct


class AnswerModel(TimedBaseMixin, BaseModel):
    __tablename__ = "answers"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(String)
    description = Column(String)
    question_id = Column(
        BigInteger,
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
