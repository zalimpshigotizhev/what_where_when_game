import pytest
from sqlalchemy import select

from app.bot.game.models import PlayerModel
from app.bot.user.models import UserModel
from tests.utils import (
    game_player_to_dict,
    game_players_to_dict,
    game_users_to_dict,
)


class TestPlayerAccessor:
    async def test_table_exists(self, inspect_list_tables: list[str]):
        assert "players" in inspect_list_tables
        assert "users" in inspect_list_tables

    @pytest.mark.asyncio
    async def test_create_player(
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

    @pytest.mark.asyncio
    async def test_get_player_by_id(
        self,
        store,
        active_player,
        db_sessionmaker,
        id_tg,
        username_tg,
    ):
        exist_player = await store.players.get_player_by_id(
            player_id=active_player.id
        )
        assert exist_player is not None
        assert game_player_to_dict(exist_player) == {
            "id": active_player.id,
            "session_id": active_player.session_id,
            "is_active": active_player.is_active,
            "is_ready": active_player.is_ready,
            "is_captain": active_player.is_captain,
            "user_id": active_player.user_id,
        }

    @pytest.mark.asyncio
    async def test_get_player_by_username_tg(
        self,
        store,
        active_player,
        db_sessionmaker,
        id_tg,
        username_tg,
    ):
        exist_player = await store.players.get_player_by_username_tg(
            session_id=active_player.session_id, username_tg=username_tg
        )
        assert exist_player is not None
        assert game_player_to_dict(exist_player) == {
            "id": active_player.id,
            "session_id": active_player.session_id,
            "is_active": active_player.is_active,
            "is_ready": active_player.is_ready,
            "is_captain": active_player.is_captain,
            "user_id": active_player.user_id,
        }

    @pytest.mark.asyncio
    async def test_get_player_by_idtg(
        self,
        store,
        active_player,
        db_sessionmaker,
        id_tg,
        username_tg,
    ):
        exist_player = await store.players.get_player_by_idtg(
            session_id=active_player.session_id, id_tg=id_tg
        )
        assert exist_player is not None
        assert game_player_to_dict(exist_player) == {
            "id": active_player.id,
            "session_id": active_player.session_id,
            "is_active": active_player.is_active,
            "is_ready": active_player.is_ready,
            "is_captain": active_player.is_captain,
            "user_id": active_player.user_id,
        }

    @pytest.mark.asyncio
    async def test_set_player_is_active(
        self,
        store,
        active_player,
        db_sessionmaker,
        id_tg,
        username_tg,
    ):
        assert active_player.is_active is True
        await store.players.set_player_is_active(
            session_id=active_player.session_id, id_tg=id_tg, new_active=False
        )

        exist_player = await store.players.get_player_by_id(
            player_id=active_player.id
        )
        assert exist_player is not None
        assert exist_player.is_active is False

    @pytest.mark.asyncio
    async def test_set_all_players_is_ready_false(
        self,
        store,
        active_game_session,
        db_sessionmaker,
        id_tg,
        username_tg,
        is_active_players,
    ):
        assert all(player.is_ready for player in is_active_players)
        await store.players.set_all_players_is_ready_false(
            session_id=active_game_session.id,
        )

        exist_sess = await store.game_session.get_active_session_by_chat_id(
            chat_id=active_game_session.chat_id, inload_players=True
        )
        assert len(exist_sess.players) == 6
        assert all(player.is_ready is False for player in exist_sess.players)

    @pytest.mark.asyncio
    async def test_set_player_is_ready(
        self,
        store,
        active_player,
        db_sessionmaker,
        id_tg,
        username_tg,
    ):
        assert active_player.is_ready is False
        await store.players.set_player_is_ready(
            session_id=active_player.session_id, id_tg=id_tg, new_active=True
        )

        exist_player = await store.players.get_player_by_id(
            player_id=active_player.id
        )
        assert exist_player is not None
        assert exist_player.is_active is True
