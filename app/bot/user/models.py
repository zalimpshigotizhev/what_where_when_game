from sqlalchemy import BigInteger, Column, String
from sqlalchemy.orm import relationship

from app.store.database.sqlalchemy_base import BaseModel, TimedBaseMixin


class UserModel(TimedBaseMixin, BaseModel):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True, autoincrement=True, unique=True)
    username_tg = Column(String, unique=True)
    # TODO: Изменить название username_id_tg на id_tg
    username_id_tg = Column(BigInteger, unique=True)
    # TODO: Добавить total_win
    players = relationship("PlayerModel", back_populates="user")
