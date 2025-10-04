from sqlalchemy import exc, select

from app.base.base_accessor import BaseAccessor
from app.bot.game.models import (
    GameState,
    PlayerModel,
    RoundModel,
    SessionModel,
    StateModel,
    StatusSession,
)
from app.bot.user.models import UserModel


# TODO: Перенести в отдельный файл
class ActiveSessionError(Exception):
    pass


class SessionGameAccessor(BaseAccessor):
    async def create_session_game(
        self,
        chat_id: int,
        status: StatusSession,
        current_state: GameState,
        current_round_id: RoundModel,
    ) -> SessionModel:
        async with await self.app.database.get_session() as session:
            stmt = select(SessionModel).where(
                SessionModel.chat_id == chat_id,
                SessionModel.status != StatusSession.CANCELLED,
                SessionModel.status != StatusSession.COMPLETED,
            )
            res = await session.execute(stmt)
            instance: StateModel = res.scalars().first()
            if instance:
                raise ActiveSessionError(
                    f"В БД уже есть чат с  {chat_id=}. "
                    f"Current session ID: {instance.id}, "
                    f"status: {instance.status}"
                )
            default_state = StateModel(current_state=current_state, data={})
            new_game_session = SessionModel(
                chat_id=chat_id,
                status=status,
                state=default_state,
                current_round_id=current_round_id,
            )
            session.add(new_game_session)
            await session.commit()
        return new_game_session

    async def get_curr_game_session_by_chat_id(
        self, chat_id: int
    ) -> SessionModel:
        async with await self.app.database.get_session() as session:
            stmt = select(SessionModel).where(
                SessionModel.chat_id == chat_id,
                SessionModel.status != StatusSession.CANCELLED,
                SessionModel.status != StatusSession.COMPLETED,
            )
            result = await session.execute(stmt)
        return result.scalars().first()

    async def is_user_in_session(self, user_id_tg: int, session_game_id: int):
        async with await self.app.database.get_session() as session:
            stmt = (
                select(PlayerModel)
                .join(UserModel)
                .where(
                    PlayerModel.session_id == session_game_id,
                    UserModel.username_id_tg == user_id_tg,
                )
            )
            result = await session.execute(stmt)
            user = result.unique().scalar_one_or_none()
        return user is not None

    async def get_or_create_user(
        self, username_tg: str, id_tg: int
    ) -> UserModel:
        async with await self.app.database.get_session() as session:
            try:
                stmt = select(UserModel).where(
                    UserModel.username_id_tg == id_tg
                )
                res = await session.execute(stmt)
                instance: UserModel = res.scalars().one_or_none()

                if instance is None:
                    new_user = UserModel(
                        username_tg=username_tg, username_id_tg=id_tg
                    )
                    session.add(new_user)
                    await session.commit()
                    return new_user

                if (
                    instance.username_id_tg == id_tg
                    and instance.username_tg != username_tg
                ):
                    instance.username_tg = username_tg
                    await session.commit()

            except exc.MultipleResultsFound as msg:
                # В случае если не один юзер в БД
                self.logger.error(msg)
                instance = res.scalars().first()
                # Елси не совпадает username_tg с username в БД
        return instance

    async def create_player(
        self,
        session_id: int,
        id_tg: int,
        username_tg,
        total_true_answers: int = 0,
        is_ready: bool = False,
        is_captain: bool = False,
    ) -> PlayerModel:
        async with await self.app.database.get_session() as session:
            user = await self.get_or_create_user(
                username_tg=username_tg, id_tg=id_tg
            )

            new_player = PlayerModel(
                session_id=session_id,
                is_ready=is_ready,
                is_captain=is_captain,
                total_true_answers=total_true_answers,
                user_id=user.id,
            )
            session.add(new_player)
            await session.commit()
        return new_player

    async def create_round(
        self,
        session_id: int,
        question_id: int,
        is_active: bool = False,
        answer_player_id: int | None = None,
        is_correct_answer: bool | None = None,
    ) -> PlayerModel:
        async with await self.app.database.get_session() as session:
            new_player = RoundModel(
                session_id=session_id,
                is_active=is_active,
                is_correct_answer=is_correct_answer,
                question_id=question_id,
                answer_player_id=answer_player_id,
            )
            session.add(new_player)
            await session.commit()
        return new_player

    async def set_round_is_active(self, round_id: int, is_active: bool):
        pass
