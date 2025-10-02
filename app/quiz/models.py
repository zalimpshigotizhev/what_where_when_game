from sqlalchemy import Column, BigInteger, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.store.database.sqlalchemy_base import BaseModel, TimedBaseMixin


class ThemeMixin(TimedBaseMixin, BaseModel):
    __tablename__ = "themes"
    id = Column(BigInteger, primary_key=True, autoincrement=True, unique=True)
    title = Column(String, unique=True)
    questions = relationship(
        "QuestionModel",
        back_populates="theme",
        cascade="all, delete-orphan"
    )


class QuestionMixin(TimedBaseMixin, BaseModel):
    __tablename__ = "questions"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(String, unique=True)
    theme_id = Column(BigInteger, ForeignKey("themes.id", ondelete="CASCADE"), nullable=False)
    theme = relationship("ThemeModel", back_populates="questions")
    true_answer = relationship("AnswerModel", uselist=False, backref="question")


class AnswerMixin(TimedBaseMixin, BaseModel):
    __tablename__ = "answers"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(String)
    question_id = Column(
        BigInteger,
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

