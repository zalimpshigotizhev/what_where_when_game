from sqlalchemy import JSON, BigInteger, Boolean, Column, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Enum

from app.bot.user.models import UserModel  # noqa: F401
from app.store.database.sqlalchemy_base import BaseModel, TimedBaseMixin

import enum


class GameState(enum.Enum):
    """Состояния бота"""

    INACTIVE = None
    WAITING_FOR_PLAYERS = "waiting_players"
    ARE_READY_FIRST_ROUND_PLAYERS = "are_ready_first_round_players"
    QUESTION_DISCUTION = "question_discussion"
    VERDICT_CAPTAIN = "verdict_captain"
    WAIT_ANSWER = "wait_answer"
    ARE_READY_NEXT_ROUND_PLAYERS = "are_ready_next_round_players"


class StatusSession(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class StateModel(TimedBaseMixin, BaseModel):
    __tablename__ = "states"
    id = Column(BigInteger, primary_key=True, autoincrement=True, unique=True)
    current_state = Column(Enum(GameState), default=GameState.INACTIVE)
    data = Column(JSON, default=dict)

    session_id = Column(BigInteger, ForeignKey("sessions.id"), unique=True)

    session = relationship(
        "SessionModel",
        back_populates="state",
        foreign_keys=[session_id],
        uselist=False,
    )


class SessionModel(TimedBaseMixin, BaseModel):
    __tablename__ = "sessions"
    id = Column(BigInteger, primary_key=True, autoincrement=True, unique=True)
    chat_id = Column(BigInteger)
    status = Column(Enum(StatusSession))
    current_round_id = Column(
        BigInteger,
        ForeignKey("rounds.id", ondelete="SET NULL"),
        unique=True,
        nullable=True,
    )

    state = relationship(
        "StateModel",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
        single_parent=True,
    )

    players = relationship(
        "PlayerModel",
        back_populates="session",
        foreign_keys="PlayerModel.session_id",
    )
    rounds = relationship(
        "RoundModel",
        back_populates="session",
        foreign_keys="RoundModel.session_id",
    )

    current_round = relationship(
        "RoundModel",
        foreign_keys=[current_round_id],
        post_update=True,
        uselist=False,
        lazy="joined",
    )


class PlayerModel(TimedBaseMixin, BaseModel):
    __tablename__ = "players"
    id = Column(BigInteger, primary_key=True, autoincrement=True, unique=True)
    session_id = Column(
        BigInteger, ForeignKey("sessions.id", ondelete="CASCADE"), unique=False
    )
    # TODO: Добавлено nullable=False
    is_active = Column(Boolean, default=True, nullable=False)
    is_ready = Column(Boolean, default=False)
    is_captain = Column(Boolean, default=False)
    user_id = Column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=False
    )

    user = relationship("UserModel", back_populates="players", lazy="joined")
    session = relationship("SessionModel", back_populates="players")
    answered_rounds = relationship(
        "RoundModel",
        back_populates="answer_player",
        foreign_keys="RoundModel.answer_player_id",
        lazy="joined",
    )


class RoundModel(TimedBaseMixin, BaseModel):
    __tablename__ = "rounds"
    id = Column(BigInteger, primary_key=True, autoincrement=True, unique=True)
    session_id = Column(
        BigInteger, ForeignKey("sessions.id", ondelete="CASCADE"), unique=False
    )
    is_active = Column(Boolean, default=False)
    is_correct_answer = Column(Boolean, default=None, nullable=True)
    question_id = Column(
        BigInteger,
        ForeignKey("questions.id", ondelete="SET NULL"),
        nullable=True,
    )
    answer_player_id = Column(
        BigInteger,
        ForeignKey("players.id", ondelete="SET NULL"),
        nullable=True,
    )

    question = relationship(
        "QuestionModel", back_populates="rounds", lazy="joined"
    )
    session = relationship(
        "SessionModel", back_populates="rounds", foreign_keys=[session_id]
    )
    answer_player = relationship(
        "PlayerModel",
        back_populates="answered_rounds",
        foreign_keys=[answer_player_id],
        lazy="joined",
    )
