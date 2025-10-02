import enum

from sqlalchemy import Column, BigInteger, ForeignKey, Boolean, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Enum

from app.store.database.sqlalchemy_base import BaseModel, TimedBaseMixin


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



class SessionModel(TimedBaseMixin, BaseModel):
    __tablename__ = "sessions"
    id = Column(BigInteger, primary_key=True, autoincrement=True, unique=True)
    status = Column(Enum(StatusSession))
    chat_id = Column(BigInteger)
    current_state = Column(Enum(GameState))
    current_round_id = Column(
        BigInteger,
        ForeignKey("rounds.id", ondelete="SET NULL"), unique=True
    )


class PlayerModel(TimedBaseMixin, BaseModel):
    __tablename__ = "players"
    id = Column(BigInteger, primary_key=True, autoincrement=True, unique=True)
    session_id = Column(
        BigInteger,
        ForeignKey("sessions.id", ondelete="CASCADE"), unique=False
    )
    is_ready = Column(Boolean, default=False)
    is_captain = Column(Boolean, default=False)
    total_true_answers = Column(Integer, default=0)
    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"), unique=False
    )


class RoundModel(TimedBaseMixin, BaseModel):
    __tablename__ = "rounds"
    id = Column(BigInteger, primary_key=True, autoincrement=True, unique=True)
    session_id = Column(
        BigInteger,
        ForeignKey("sessions.id", ondelete="CASCADE"), unique=False
    )
    is_active = Column(Boolean, default=False)
    is_correct_answer = Column(Boolean, default=False)
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

