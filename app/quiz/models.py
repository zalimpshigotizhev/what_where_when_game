from sqlalchemy import Column, BigInteger, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.store.database.sqlalchemy_base import BaseModel, TimedBaseMixin
from app.bot.game.models import RoundModel


class ThemeModel(TimedBaseMixin, BaseModel):
    __tablename__ = "themes"
    id = Column(BigInteger, primary_key=True, autoincrement=True, unique=True)
    title = Column(String, unique=True)
    questions = relationship(
        "QuestionModel",
        back_populates="theme",
        cascade="all, delete-orphan"
    )


class QuestionModel(TimedBaseMixin, BaseModel):
    __tablename__ = "questions"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(String, unique=True)
    theme_id = Column(BigInteger, ForeignKey("themes.id", ondelete="CASCADE"), nullable=False, unique=False)

    theme = relationship("ThemeModel", back_populates="questions")
    true_answer = relationship("AnswerModel", uselist=False, backref="question")
    rounds = relationship('RoundModel', back_populates="question")


class AnswerModel(TimedBaseMixin, BaseModel):
    __tablename__ = "answers"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(String)
    question_id = Column(
        BigInteger,
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

