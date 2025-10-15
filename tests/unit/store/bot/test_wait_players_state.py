from unittest.mock import AsyncMock

import pytest

from app.bot.game.models import GameState
from app.store.bot import consts
from app.store.bot.gamebot.wait_players_state import WaitingPlayersProcessGameBot


class TestWaitingPlayersProcessGameBot:

    @pytest.fixture
    def wait_p_state(self, mock_app):
        wait_player_state = WaitingPlayersProcessGameBot(mock_app)
        return wait_player_state

    @pytest.mark.asyncio
    async def test_initialization(self, bot_base, mock_app):
        """Тест инициализации BotBase"""
        assert bot_base.app == mock_app
        assert bot_base.handlers is not None

        assert bot_base.game_store == bot_base.app.store.game_session

    async def test_handle_join_game_dont_exist_game(
            self,
            bot_base,
            chat_id,
            session_id,
            session_game,
            wait_p_state,
            callback
    ):
        """
        Тест на то, что игры не существует.
        """
        callback.data = "join_game"
        wait_p_state.game_store.get_active_session_by_chat_id = AsyncMock(
            return_value=None
        )
        await wait_p_state.handle_join_game(
            callback, GameState.WAITING_FOR_PLAYERS
        )

        wait_p_state.app.store.tg_api.answer_callback_query.assert_called_once_with(
            callback_query_id=callback.id_,
            text=consts.GAME_DONT_EXIST,
        )

    async def test_handle_join_game_enough_players(
            self,
            bot_base,
            chat_id,
            session_id,
            session_game,
            wait_p_state,
            callback,
            full_players,
            player7
    ):
        """
        Тест на то, что максимальное кол-ство игроков
        уже подключена к сессии и кто-то пытается
        подключиться.
        """
        callback.data = "join_game"
        session_game.players = full_players


        wait_p_state.game_store.get_active_session_by_chat_id = AsyncMock(
            return_value=session_game
        )
        await wait_p_state.handle_join_game(
            callback, GameState.WAITING_FOR_PLAYERS
        )

        wait_p_state.app.store.tg_api.answer_callback_query.assert_called_once_with(
            callback_query_id=callback.id_,
            text="Набралось достаточное кол-ство человек",
        )

    async def test_handle_join_game_already_joined(
            self,
            bot_base,
            chat_id,
            session_id,
            session_game,
            wait_p_state,
            callback,
            full_players,
            player6
    ):
        """
        Тест на то, что игрок, который пытается присоединиться к игре,
        уже подключен к сессии
        """
        callback.data = "join_game"
        callback.from_.username = player6.user.username_tg
        callback.from_.id_ = player6.user.id_tg



        session_game.players = full_players


        wait_p_state.game_store.get_active_session_by_chat_id = AsyncMock(
            return_value=session_game
        )
        await wait_p_state.handle_join_game(
            callback, GameState.WAITING_FOR_PLAYERS
        )

        wait_p_state.app.store.tg_api.answer_callback_query.assert_called_once_with(
            callback_query_id=callback.id_,
            text=consts.YOU_APPLY_TO_READY,
        )

    async def test_handle_join_game_joined_is_not_active(
            self,
            chat_id,
            session_id,
            session_game,
            wait_p_state,
            callback,
            full_players,
            player6
    ):
        """
        Тест на то, что игрок, который пытается присоединиться к игре, но
        есть PlayerModel.is_active == False, в таком случае
        """
        wait_p_state.add_message_in_unnecessary_messages = AsyncMock()
        callback.data = "join_game"
        target_player = full_players[-1]
        callback.from_.username = target_player.user.username_tg
        callback.from_.id_ = target_player.user.id_tg

        # Устанавливаем is_active = False
        target_player.is_active = False

        # Убедимся, что session_game.players содержит обновленных игроков
        session_game.players = full_players

        # Добавим отладочную проверку
        wait_p_state.game_store.get_active_session_by_chat_id = AsyncMock(
            return_value=session_game
        )
        await wait_p_state.handle_join_game(
            callback, GameState.WAITING_FOR_PLAYERS
        )

        wait_p_state.app.store.tg_api.answer_callback_query.assert_called_once_with(
            callback_query_id=callback.id_,
            text=consts.YOU_PLAYER_WITH_GAME
        )
        wait_p_state.player_store.set_player_is_active.assert_called_once_with(
            session_id=session_id,
            id_tg=callback.from_.id_, new_active=True
        )
        wait_p_state.app.store.tg_api.send_message.assert_called_once_with(
            chat_id=chat_id,
            text=consts.PLAYER_JOINED.format(username=callback.from_.username),
        )
        wait_p_state.add_message_in_unnecessary_messages.assert_called()


    async def test_handle_join_game(
            self,
            chat_id,
            session_id,
            session_game,
            wait_p_state,
            callback,
            full_players,
            player7
    ):
        """
        Тест на то, что игрок, который пытается присоединиться к игре и
        создается PlayerModel
        """
        wait_p_state.add_message_in_unnecessary_messages = AsyncMock()
        callback.data = "join_game"
        callback.from_.username = player7.user.username_tg
        callback.from_.id_ = player7.user.id_tg

        full_players[-1].is_active = False

        # Убедимся, что session_game.players содержит обновленных игроков
        session_game.players = full_players

        # Добавим отладочную проверку
        wait_p_state.game_store.get_active_session_by_chat_id = AsyncMock(
            return_value=session_game
        )
        await wait_p_state.handle_join_game(
            callback, GameState.WAITING_FOR_PLAYERS
        )

        wait_p_state.app.store.tg_api.answer_callback_query.assert_called_once_with(
            callback_query_id=callback.id_,
            text=consts.YOU_PLAYER_WITH_GAME
        )
        wait_p_state.player_store.create_player.assert_called_once_with(
            session_id=session_id,
            id_tg=callback.from_.id_,
            username_tg=callback.from_.username,
        )
        wait_p_state.app.store.tg_api.send_message.assert_called_once_with(
            chat_id=chat_id,
            text=consts.PLAYER_JOINED.format(username=callback.from_.username),
        )
        wait_p_state.add_message_in_unnecessary_messages.assert_called()

    async def test_handle_start_game_from_captain_dont_exist_session(
            self,
            chat_id,
            session_id,
            session_game,
            wait_p_state,
            callback,
            full_players,
            player7
    ):
        """
        Тест на то, что игрок, который пытается присоединиться к игре,
        уже подключен к сессии
        """
        wait_p_state.add_message_in_unnecessary_messages = AsyncMock()
        callback.data = "start_game_from_captain"

        wait_p_state.game_store.get_active_session_by_chat_id = AsyncMock(
            return_value=None
        )
        await wait_p_state.handle_start_game_from_captain(
            callback, GameState.WAITING_FOR_PLAYERS
        )

        wait_p_state.app.store.tg_api.answer_callback_query.assert_called_once_with(
            callback_query_id=callback.id_,
            text=consts.GAME_DONT_EXIST,
        )

    async def test_handle_start_game_from_captain_dont_paricipant(
            self,
            chat_id,
            session_id,
            session_game,
            wait_p_state,
            callback,
            full_players,
            player7
    ):
        """
        Тест на то, что игрок, который пытается присоединиться к игре,
        уже подключен к сессии
        """
        wait_p_state.add_message_in_unnecessary_messages = AsyncMock()
        callback.data = "start_game_from_captain"
        callback.from_.username = player7.user.username_tg
        callback.from_.id_ = player7.user.id_tg

        session_game.players = full_players
        wait_p_state.game_store.get_active_session_by_chat_id = AsyncMock(
            return_value=session_game
        )
        await wait_p_state.handle_start_game_from_captain(
            callback, GameState.WAITING_FOR_PLAYERS
        )

        wait_p_state.app.store.tg_api.answer_callback_query.assert_called_once_with(
            callback_query_id=callback.id_,
            text=consts.YOU_DONT_PLAYER,
        )

    async def test_handle_start_game_from_captain_dont_enough(
            self,
            chat_id,
            session_id,
            session_game,
            wait_p_state,
            callback,
            player1,

    ):
        """
        Тест на то, что капитан, но участников меньше чем минимальное
        кол-ство игроков
        """
        wait_p_state.add_message_in_unnecessary_messages = AsyncMock()
        callback.data = "start_game_from_captain"
        callback.from_.username = player1.user.username_tg
        callback.from_.id_ = player1.user.id_tg

        session_game.players = [
            player1
        ]
        wait_p_state.game_store.get_active_session_by_chat_id = AsyncMock(
            return_value=session_game
        )
        await wait_p_state.handle_start_game_from_captain(
            callback, GameState.WAITING_FOR_PLAYERS
        )

        wait_p_state.app.store.tg_api.answer_callback_query.assert_called_once_with(
            callback_query_id=callback.id_,
            text=consts.LESS_MIN_PLAYERS,
        )

    async def test_handle_start_game_from_captain_just_player(
            self,
            chat_id,
            session_id,
            session_game,
            wait_p_state,
            callback,
            full_players,
            player5,

    ):
        """
        Тест на то, что капитан, но участников меньше чем минимальное
        кол-ство игроков
        """
        wait_p_state.add_message_in_unnecessary_messages = AsyncMock()
        callback.data = "start_game_from_captain"
        callback.from_.username = player5.user.username_tg
        callback.from_.id_ = player5.user.id_tg

        session_game.players = full_players
        wait_p_state.game_store.get_active_session_by_chat_id = AsyncMock(
            return_value=session_game
        )
        await wait_p_state.handle_start_game_from_captain(
            callback, GameState.WAITING_FOR_PLAYERS
        )

        wait_p_state.app.store.tg_api.answer_callback_query.assert_called_once_with(
            callback_query_id=callback.id_,
            text=consts.GAME_START_ONLY_CAP,
        )

    async def test_handle_start_game_from_captain(
            self,
            chat_id,
            session_id,
            session_game,
            wait_p_state,
            callback,
            full_players,
            player1,

    ):
        """
        Тест на то, что капитан, но участников меньше чем минимальное
        кол-ство игроков
        """
        wait_p_state.add_message_in_unnecessary_messages = AsyncMock()
        wait_p_state.deleted_unnecessary_messages = AsyncMock()
        wait_p_state.next_quest = AsyncMock()

        callback.data = "start_game_from_captain"
        callback.from_.username = player1.user.username_tg
        callback.from_.id_ = player1.user.id_tg

        session_game.players = full_players
        wait_p_state.game_store.get_active_session_by_chat_id = AsyncMock(
            return_value=session_game
        )
        await wait_p_state.handle_start_game_from_captain(
            callback, GameState.WAITING_FOR_PLAYERS
        )

        wait_p_state.app.store.tg_api.answer_callback_query.assert_called_once_with(
            callback_query_id=callback.id_,
            text=consts.STARTED_GAME_FOR_CAP,
        )
        wait_p_state.deleted_unnecessary_messages.assert_called()
        wait_p_state.next_quest.assert_called_once_with(
            text=consts.ARE_YOU_READY_FIRST_QUEST,
            chat_id=chat_id,
            session_id=session_id,
        )

    async def test_handle_finish_game_dont_exist_session(
            self,
            chat_id,
            session_id,
            session_game,
            wait_p_state,
            callback,
            full_players,
            player1,

    ):
        """
        Тест на кнопку "закончить игру"
        """
        wait_p_state.add_message_in_unnecessary_messages = AsyncMock()
        wait_p_state.deleted_unnecessary_messages = AsyncMock()

        callback.data = "finish_game"

        wait_p_state.game_store.get_active_session_by_chat_id = AsyncMock(
            return_value=None
        )
        await wait_p_state.handle_finish_game(
            callback, GameState.WAITING_FOR_PLAYERS
        )

        wait_p_state.app.store.tg_api.answer_callback_query.assert_called_once_with(
            callback_query_id=callback.id_,
            text=consts.GAME_DONT_EXIST,
        )
    async def test_handle_finish_game_is_dont_participant(
            self,
            chat_id,
            session_id,
            session_game,
            wait_p_state,
            callback,
            full_players,
            player7,

    ):
        """
        Тест на кнопку "закончить игру"
        """
        wait_p_state.add_message_in_unnecessary_messages = AsyncMock()
        wait_p_state.deleted_unnecessary_messages = AsyncMock()

        callback.data = "finish_game"
        callback.from_.username = player7.user.username_tg
        callback.from_.id_ = player7.user.id_tg

        session_game.players = full_players
        wait_p_state.game_store.get_active_session_by_chat_id = AsyncMock(
            return_value=session_game
        )
        await wait_p_state.handle_finish_game(
            callback, GameState.WAITING_FOR_PLAYERS
        )

        wait_p_state.app.store.tg_api.answer_callback_query.assert_called_once_with(
            callback_query_id=callback.id_,
            text=consts.YOU_DONT_PLAYER,
        )

    async def test_handle_finish_game_is_captain(
            self,
            chat_id,
            session_id,
            session_game,
            wait_p_state,
            callback,
            full_players,
            player1,

    ):
        """
        Тест на кнопку "закончить игру"
        """
        wait_p_state.add_message_in_unnecessary_messages = AsyncMock()
        wait_p_state.cancel_game = AsyncMock()

        callback.data = "finish_game"
        callback.from_.username = player1.user.username_tg
        callback.from_.id_ = player1.user.id_tg

        session_game.players = full_players
        wait_p_state.game_store.get_active_session_by_chat_id = AsyncMock(
            return_value=session_game
        )
        await wait_p_state.handle_finish_game(
            callback, GameState.WAITING_FOR_PLAYERS
        )

        wait_p_state.cancel_game.assert_called_once_with(
                current_chat_id=chat_id, session_id=session_id
            )
        wait_p_state.app.store.tg_api.answer_callback_query.assert_called_once_with(
            callback_query_id=callback.id_,
            text=consts.YOU_CAP_AND_YOU_FINISH_GAME,
        )

    async def test_handle_finish_game_is_not_captain(
            self,
            chat_id,
            session_id,
            session_game,
            wait_p_state,
            callback,
            full_players,
            player2,

    ):
        """
        Тест на кнопку "закончить игру"
        """
        wait_p_state.add_message_in_unnecessary_messages = AsyncMock()
        wait_p_state.cancel_game = AsyncMock()

        callback.data = "finish_game"
        callback.from_.username = player2.user.username_tg
        callback.from_.id_ = player2.user.id_tg

        session_game.players = full_players
        wait_p_state.game_store.get_active_session_by_chat_id = AsyncMock(
            return_value=session_game
        )
        await wait_p_state.handle_finish_game(
            callback, GameState.WAITING_FOR_PLAYERS
        )

        wait_p_state.player_store.set_player_is_active.assert_called_once_with(
                session_id=session_id, id_tg=callback.from_.id_, new_active=False
        )

        wait_p_state.app.store.tg_api.send_message.assert_called_once_with(
            chat_id=chat_id,
            text=consts.PLAYER_EXIT.format(
                username=callback.from_.username
            ),
        )
        wait_p_state.app.store.tg_api.answer_callback_query.assert_called_once_with(
            callback_query_id=callback.id_,
            text=consts.YOU_EXIT_GAME
        )
        wait_p_state.add_message_in_unnecessary_messages.assert_called()