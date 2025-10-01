from sqlalchemy import Column, BigInteger, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.store.database.sqlalchemy_base import BaseModel


class ThemeModel(BaseModel):
    __tablename__ = "themes"
    id = Column(BigInteger, primary_key=True, autoincrement=True, unique=True)
    title = Column(String, unique=True)
    questions = relationship(
        "QuestionModel",
        back_populates="theme",
        cascade="all, delete-orphan"
    )


class QuestionModel(BaseModel):
    __tablename__ = "questions"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(String, unique=True)
    theme_id = Column(BigInteger, ForeignKey("themes.id", ondelete="CASCADE"), nullable=False)
    theme = relationship("ThemeModel", back_populates="questions")
    answers = relationship("AnswerModel", back_populates="question", lazy='subquery')


class AnswerModel(BaseModel):
    __tablename__ = "answers"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(String)
    is_correct = Column(Boolean)
    question_id = Column(BigInteger, ForeignKey("questions.id", ondelete="CASCADE"))  # Внешний ключ

    question = relationship("QuestionModel", back_populates="answers")