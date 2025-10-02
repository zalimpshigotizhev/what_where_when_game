from sqlalchemy import Column, DateTime
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.functions import func


class BaseModel(DeclarativeBase):
    pass


class TimedBaseMixin:
    @declared_attr
    def created_at(self):
        return Column(DateTime(timezone=True), server_default=func.now())

    @declared_attr
    def updated_at(self):
        return Column(DateTime(timezone=True), onupdate=func.now())
