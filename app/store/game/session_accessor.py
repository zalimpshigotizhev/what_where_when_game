from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.base.base_accessor import BaseAccessor
from app.bot.game.models import (
    GameState,
    SessionModel,
    StateModel,
    StatusSession,
)


class GameSessionAccessor(BaseAccessor):
    async def create_state(
        self, session_id: int, current_state: GameState, data: dict
    ) -> StateModel:
        """Создаем состояние
        :param session_id: SessionModel.id
        :param current_state: GameState ->
        [INACTIVE,
        WAITING_FOR_PLAYERS, ARE_READY_FIRST_ROUND_PLAYERS,
        QUESTION_DISCUTION, VERDICT_CAPTAIN,
        WAIT_ANSWER, ARE_READY_NEXT_ROUND_PLAYERS]

        :param data: По дефолту dict() в БД
        :return:
        """
        async with await self.app.database.get_session() as session:
            new_state = StateModel(
                session_id=session_id, current_state=current_state, data=data
            )
            session.add(new_state)
            await session.commit()
            return new_state

    async def create_session(
        self,
        chat_id: int,
        status: StatusSession,
    ) -> SessionModel:
        """Создает сессию и состояние к ней автоматически.
        :param chat_id: Telegram chat_id
        :param status: StatusSession ->
                [PENDING, PROCESSING,COMPLETED, CANCELLED]
        :return:
        """
        async with await self.app.database.get_session() as session:
            new_session = SessionModel(chat_id=chat_id, status=status)
            session.add(new_session)
            await session.commit()
            await session.refresh(new_session)

            await self.create_state(
                session_id=new_session.id,
                current_state=GameState.INACTIVE,
                data={},
            )
            return new_session

    async def get_session_by_id(
        self,
        session_id: int,
    ) -> SessionModel | None:
        """Находит по id сессию
        :param session_id: SessionModel.id
        :return: SessionModel
        """
        async with await self.app.database.get_session() as session:
            stmt = select(SessionModel).filter_by(id=session_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_active_session_by_chat_id(
        self,
        chat_id: int,
        inload_players: bool = False,
    ) -> SessionModel | None:
        """Возвращает сессию у которой:
        SessionModel.status in
        [StatusSession.PENDING, StatusSession.PROCESSING].
        Вызывается исключение в случае если в БД не один такой экземпляр.
        :param chat_id: Telegram chat_id
        :param inload_players: Подгрузить ли связных игроков?
        :return: SessionModel
        """
        async with await self.app.database.get_session() as session:
            stmt = select(SessionModel).filter_by(chat_id=chat_id)

            stmt = stmt.where(
                SessionModel.status.notin_(
                    [StatusSession.CANCELLED, StatusSession.COMPLETED]
                )
            )
            if inload_players:
                stmt = stmt.options(selectinload(SessionModel.players))

            result = await session.execute(stmt)
            return result.scalars().one_or_none()

    async def set_status(
        self, session_id: int, new_status: StatusSession
    ) -> SessionModel:
        """Обновляет SessionModel.status
        :param session_id: SessionModel.id
        :param new_status: StatusSession ->
                [PENDING, PROCESSING, COMPLETED, CANCELLED]
        :return: Обновленный SessionModel
        """
        async with await self.app.database.get_session() as session:
            stmt = select(SessionModel).filter_by(id=session_id)

            result = await session.execute(stmt)
            game_session: SessionModel = result.scalars().one_or_none()
            game_session.status = new_status
            await session.commit()
            return game_session
