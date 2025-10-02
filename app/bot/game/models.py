from sqlalchemy import Column, BigInteger, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.store.database.sqlalchemy_base import BaseModel, TimedBaseMixin


# class Players(TimedBaseMixin, BaseModel):
