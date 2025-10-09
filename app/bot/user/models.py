from sqlalchemy import BigInteger, Column, String
from sqlalchemy.orm import relationship

from app.store.database.sqlalchemy_base import BaseModel, TimedBaseMixin


class UserModel(TimedBaseMixin, BaseModel):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True, autoincrement=True, unique=True)
    username_tg = Column(String, unique=True)
    id_tg = Column(BigInteger, unique=True)
    players = relationship("PlayerModel", back_populates="user")
