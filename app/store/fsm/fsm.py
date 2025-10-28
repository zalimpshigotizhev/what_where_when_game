import typing
from abc import ABC, abstractmethod

from sqlalchemy import select

from app.bot.game.models import (
    GameState,
    SessionModel,
    StateModel,
    StatusSession,
)

if typing.TYPE_CHECKING:
    from app.web.app import Application


class StateStorageABC(ABC):
    @abstractmethod
    async def get_state(self, chat_id: int):
        pass

    @abstractmethod
    async def set_state(self, chat_id: int, new_state):
        pass

    @abstractmethod
    async def update_data(self, chat_id: int, **kwargs) -> dict:
        pass

    @abstractmethod
    async def get_data(self, chat_id: int) -> dict:
        pass

    @abstractmethod
    async def clear_data(self, chat_id: int):
        pass


class BaseStorage:
    def __init__(self, app: "Application"):
        self.app = app


# class MemoryStorageABC(StateStorageABC, BaseStorage):
#     def get_state(self, chat_id: int):
#         query = db_states.get(chat_id)
#         if query is None:
#             query = self.set_state(chat_id=chat_id, state=GameState.INACTIVE)
#         return query.get("state")
#
#     def set_state(self, chat_id: int, state: GameState):
#         query = db_states.get(chat_id)
#         if query:
#             query["state"] = state
#         else:
#             db_states[chat_id] = {"state": state, "data": {}}
#             query = db_states[chat_id]
#         return query
#
#     def update_data(self, chat_id: int, **kwargs):
#         query = db_states.get(chat_id)
#         if query is None:
#             query = self.set_state(chat_id, GameState.INACTIVE)
#
#         query["data"] = kwargs
#
#     def get_data(self, chat_id: int):
#         query = db_states.get(chat_id)
#         if query is None:
#             query = self.set_state(chat_id, GameState.INACTIVE)
#         return query["data"]
#
#     def clear_data(self, chat_id: int):
#         query = db_states.get(chat_id)
#         if query is None:
#             query = self.set_state(chat_id, GameState.INACTIVE)
#         del query["data"]


class PostgresAsyncStorage(StateStorageABC, BaseStorage):
    async def get_state(self, chat_id: int):
        async with await self.app.database.get_session() as session:
            stmt = (
                select(StateModel.current_state)
                .join(SessionModel)
                .where(
                    SessionModel.chat_id == chat_id,
                    SessionModel.status != StatusSession.COMPLETED,
                    SessionModel.status != StatusSession.CANCELLED,
                    StateModel.session_id == SessionModel.id,
                )
            )
            res = await session.execute(stmt)
            return res.scalars().one_or_none()

    async def set_state(self, chat_id: int, new_state: "GameState") -> None:
        async with await self.app.database.get_session() as session:
            stmt = (
                select(StateModel)
                .join(SessionModel)
                .where(
                    SessionModel.chat_id == chat_id,
                    SessionModel.status != StatusSession.COMPLETED,
                    SessionModel.status != StatusSession.CANCELLED,
                    StateModel.session_id == SessionModel.id,
                )
            )
            res = await session.execute(stmt)
            state: StateModel = res.scalars().one_or_none()
            state.current_state = new_state
            await session.commit()

    async def update_data(self, chat_id: int, new_data: dict) -> None:
        async with await self.app.database.get_session() as session:
            stmt = (
                select(StateModel)
                .join(SessionModel)
                .where(
                    SessionModel.chat_id == chat_id,
                    SessionModel.status != StatusSession.COMPLETED,
                    SessionModel.status != StatusSession.CANCELLED,
                    StateModel.session_id == SessionModel.id,
                )
            )
            res = await session.execute(stmt)
            state: StateModel = res.scalars().one_or_none()
            state.data = new_data
            await session.commit()

    async def get_data(self, chat_id: int) -> dict:
        async with await self.app.database.get_session() as session:
            stmt = (
                select(StateModel.data)
                .join(SessionModel)
                .where(
                    SessionModel.chat_id == chat_id,
                    SessionModel.status != StatusSession.COMPLETED,
                    SessionModel.status != StatusSession.CANCELLED,
                    StateModel.session_id == SessionModel.id,
                )
            )
            res = await session.execute(stmt)
            return res.scalars().one_or_none()

    async def clear_data(self, chat_id: int):
        async with await self.app.database.get_session() as session:
            stmt = (
                select(StateModel)
                .join(SessionModel)
                .where(
                    SessionModel.chat_id == chat_id,
                    SessionModel.status != StatusSession.COMPLETED,
                    SessionModel.status != StatusSession.CANCELLED,
                    StateModel.session_id == SessionModel.id,
                )
            )
            res = await session.execute(stmt)
            state: StateModel = res.scalars().one_or_none()
            state.data = {}
            await session.commit()


class FSMContext:
    """Контекст FSM для хранения состояния пользователя/чата"""

    def __init__(self, app: "Application"):
        self.app = app
        self.storage: StateStorageABC = PostgresAsyncStorage(app)

    async def get_state(self, chat_id: int):
        return await self.storage.get_state(chat_id=chat_id)

    async def set_state(self, chat_id: int, new_state) -> None:
        return await self.storage.set_state(
            chat_id=chat_id, new_state=new_state
        )

    async def update_data(self, chat_id: int, new_data: dict) -> dict:
        return await self.storage.update_data(
            chat_id=chat_id, new_data=new_data
        )

    async def get_data(self, chat_id: int) -> dict:
        return await self.storage.get_data(chat_id=chat_id)

    async def clear_data(self, chat_id: int) -> None:
        return await self.storage.clear_data(chat_id=chat_id)
