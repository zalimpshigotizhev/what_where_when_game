import pytest
from sqlalchemy import select

from app.bot.game.models import PlayerModel
from app.bot.user.models import UserModel
from tests.utils import game_players_to_dict, game_users_to_dict


class TestPlayerAccessor:
    async def test_table_exists(self, inspect_list_tables: list[str]):
        assert "players" in inspect_list_tables
        assert "users" in inspect_list_tables

    @pytest.mark.asyncio
    async def test_create_session(
        self,
        store,
        active_game_session,
        db_sessionmaker,
        id_tg,
        username_tg,
    ):
        new_player = await store.players.create_player(
            session_id=active_game_session.id,
            id_tg=id_tg,
            username_tg=username_tg,
            is_active=True,
            is_ready=False,
            is_captain=False,
        )

        assert new_player is not None
        assert isinstance(new_player, PlayerModel)

        async with db_sessionmaker() as sess:
            users = await sess.execute(select(UserModel))
            players = await sess.execute(select(PlayerModel))

            users_list = users.unique().scalars()
            players_list = players.unique().scalars()

        player = await store.players.get_player_by_id(player_id=new_player.id)

        assert game_users_to_dict(users_list) == [
            {
                "id": player.user.id,
                "id_tg": player.user.id_tg,
                "username_tg": player.user.username_tg,
            }
        ]

        assert game_players_to_dict(players_list) == [
            {
                "id": player.id,
                "session_id": active_game_session.id,
                "is_active": player.is_active,
                "is_ready": player.is_ready,
                "is_captain": player.is_captain,
                "user_id": player.user_id,
            }
        ]
