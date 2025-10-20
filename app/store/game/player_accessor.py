from sqlalchemy import select

from app.base.base_accessor import BaseAccessor
from app.bot.game.models import PlayerModel
from app.bot.user.models import UserModel


class PlayerAccessor(BaseAccessor):
    async def create_player(
        self,
        session_id: int,
        id_tg: int,
        username_tg: str,
        is_active: bool = True,
        is_ready: bool = False,
        is_captain: bool = False,
    ) -> PlayerModel:
        user = await self.app.store.users.get_or_create(
            id_tg=id_tg,
            username_tg=username_tg,
        )

        async with await self.app.database.get_session() as session:
            new_player = PlayerModel(
                session_id=session_id,
                is_active=is_active,
                is_ready=is_ready,
                is_captain=is_captain,
                user_id=user.id,
            )
            session.add(new_player)
            await session.commit()
            return new_player

    async def get_player_by_id(
        self,
        player_id: int,
    ) -> PlayerModel | None:
        async with await self.app.database.get_session() as session:
            stmt = select(PlayerModel).filter_by(id=player_id)

            result = await session.execute(stmt)
            return result.unique().scalar_one_or_none()

    async def get_player_by_username_tg(
        self,
        session_id: int,
        username_tg: int,
    ) -> PlayerModel | None:
        async with await self.app.database.get_session() as session:
            stmt = (
                select(PlayerModel)
                .join(PlayerModel.user)
                .where(
                    PlayerModel.session_id == session_id,
                    UserModel.username_tg == username_tg,
                )
            )
            result = await session.execute(stmt)
            return result.unique().scalar_one_or_none()

    async def get_player_by_idtg(
        self,
        session_id: int,
        id_tg: int,
    ) -> PlayerModel | None:
        async with await self.app.database.get_session() as session:
            stmt = (
                select(PlayerModel)
                .join(PlayerModel.user)
                .where(
                    PlayerModel.session_id == session_id,
                    UserModel.id_tg == id_tg,
                )
            )
            result = await session.execute(stmt)
            return result.unique().scalar_one_or_none()

    async def set_player_is_active(
        self, session_id: int, id_tg: int, new_active: bool
    ) -> PlayerModel | None:
        async with await self.app.database.get_session() as session:
            stmt = (
                select(PlayerModel)
                .join(PlayerModel.user)
                .where(
                    PlayerModel.session_id == session_id,
                    UserModel.id_tg == id_tg,
                )
            )
            result = await session.execute(stmt)
            exist_player: PlayerModel = result.unique().scalar_one_or_none()
            exist_player.is_active = new_active
            await session.commit()
            return exist_player

    async def set_player_is_ready(
        self, session_id: int, id_tg: int, new_active: bool
    ) -> PlayerModel | None:
        async with await self.app.database.get_session() as session:
            stmt = (
                select(PlayerModel)
                .join(PlayerModel.user)
                .where(
                    PlayerModel.session_id == session_id,
                    UserModel.id_tg == id_tg,
                )
            )
            result = await session.execute(stmt)
            exist_player: PlayerModel = result.unique().scalar_one_or_none()
            exist_player.is_ready = new_active
            await session.commit()
            return exist_player

    async def set_all_players_is_ready_false(self, session_id: int) -> None:
        async with await self.app.database.get_session() as session:
            stmt = select(PlayerModel).where(
                PlayerModel.session_id == session_id,
                PlayerModel.is_active.is_(True),
                PlayerModel.is_ready.is_(True),
            )
            result = await session.execute(stmt)
            players = result.unique().scalars().all()
            for player in players:
                player.is_ready = False
            await session.commit()
