from sqlalchemy import exc, select
from sqlalchemy.orm import selectinload

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


class ExistPlayerForSessionError(Exception):
    pass


class OldAccessor(BaseAccessor):
    async def create_or_exist_session_game(
        self,
        chat_id: int,
        status: StatusSession,
        current_state: GameState,
        current_round_id: RoundModel,
    ) -> SessionModel:
        async with await self.app.database.get_session() as session:
            # Проверяем есть ли уже сессия
            stmt = select(SessionModel).where(
                SessionModel.chat_id == chat_id,
                SessionModel.status != StatusSession.CANCELLED,
                SessionModel.status != StatusSession.COMPLETED,
            )
            res = await session.execute(stmt)
            instance: SessionModel = res.scalars().first()

            if instance is not None:
                # Если есть сессия которая в процессе игры,
                # то вызываем исключения
                if instance.status == StatusSession.PROCESSING:
                    raise ActiveSessionError(
                        f"В БД уже есть чат с  {chat_id=}. "
                        f"Current session ID: {instance.id}, "
                        f"status: {instance.status}"
                    )
                # Если есть сессия StatusSession.PENDING,
                # то просто возвращаем его и ничего не происходит
                return instance

            # Если сессии нет - создаём
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

    async def set_status_game(
        self,
        session_id: int,
        new_status_game: StatusSession,
    ) -> SessionModel:
        async with await self.app.database.get_session() as session:
            stmt = select(SessionModel).where(
                SessionModel.id == session_id,
                SessionModel.status != StatusSession.CANCELLED,
                SessionModel.status != StatusSession.COMPLETED,
            )
            result = await session.execute(stmt)
            instance: SessionModel = result.scalars().one_or_none()
            if instance is None:
                self.app.logger.error(
                    "Попытка поменять статус у несуществующей сессии"
                )
            instance.status = new_status_game
            await session.commit()
        return instance

    async def get_curr_game_session(self, chat_id: int) -> SessionModel:
        async with await self.app.database.get_session() as session:
            stmt = select(SessionModel).where(
                SessionModel.chat_id == chat_id,
                SessionModel.status != StatusSession.CANCELLED,
                SessionModel.status != StatusSession.COMPLETED,
            )
            result = await session.execute(stmt)
        return result.scalars().first()

    async def get_session_participants(
        self, session_game_id: int, active_only: bool | None = None
    ) -> list[PlayerModel]:
        async with await self.app.database.get_session() as session:
            stmt = select(PlayerModel).where(
                PlayerModel.session_id == session_game_id
            )

            if active_only is True:
                stmt = stmt.where(PlayerModel.is_active is True)
            elif active_only is False:
                stmt = stmt.where(PlayerModel.is_active is False)

            stmt = stmt.options(selectinload(PlayerModel.user))

            result = await session.execute(stmt)
            players = result.unique().scalars().all()

        return list(players)

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

    async def create_or_activity_player(
        self,
        session_game_id: int,
        id_tg: int,
        username_tg,
        total_true_answers: int = 0,
        is_active: bool = True,
        is_ready: bool = False,
        is_captain: bool = False,
    ) -> PlayerModel:
        async with await self.app.database.get_session() as session:
            user = await self.get_or_create_user(
                username_tg=username_tg, id_tg=id_tg
            )

            stmt = (
                select(PlayerModel)
                .join(UserModel)
                .where(
                    PlayerModel.session_id == session_game_id,
                    UserModel.username_id_tg == id_tg,
                    # PlayerModel.is_active is False,
                )
            )
            result = await session.execute(stmt)
            instance: PlayerModel = result.unique().scalar_one_or_none()
            if instance is not None:
                # Если player существует просто is_active=False,
                # а это происходит когда player подключился к сессии
                # потом вышел из игры,
                # то у него должна быть возможность присоединиться обратно
                if instance.is_active is False:
                    instance.is_active = True
                    await session.commit()
                    return instance

                if instance.is_active is True:
                    raise ExistPlayerForSessionError(
                        "Уже существует player для этого user в этом session"
                    )

            new_player = PlayerModel(
                session_id=session_game_id,
                is_ready=is_ready,
                is_active=is_active,
                is_captain=is_captain,
                total_true_answers=total_true_answers,
                user_id=user.id,
            )
            session.add(new_player)
            await session.commit()
        return new_player

    async def get_player(
        self, session_game_id: int, tg_id: int
    ) -> PlayerModel | None:
        async with await self.app.database.get_session() as session:
            stmt = (
                select(PlayerModel)
                .join(UserModel)
                .where(
                    PlayerModel.session_id == session_game_id,
                    UserModel.username_id_tg == tg_id,
                )
            )
            result = await session.execute(stmt)
            player: PlayerModel = result.unique().scalar_one_or_none()
            return player

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
