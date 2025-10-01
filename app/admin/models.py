from sqlalchemy import Column, BigInteger, String

from app.store.database.sqlalchemy_base import BaseModel


class AdminModel(BaseModel):
    __tablename__ = "admins"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)