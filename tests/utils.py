from collections.abc import Iterable

from app.bot.game.models import PlayerModel, SessionModel, StateModel
from app.bot.user.models import UserModel


def game_session_to_dict(game_session: SessionModel) -> dict:
    return {
        "id": game_session.id,
        "chat_id": game_session.chat_id,
        "status": game_session.status,
        "current_round_id": game_session.current_round_id,
    }


def game_sessions_to_dict(game_sessions: Iterable[SessionModel]) -> list[dict]:
    return [game_session_to_dict(session) for session in game_sessions]


def game_state_to_dict(state: StateModel) -> dict:
    return {
        "id": state.id,
        "session_id": state.session_id,
        "current_state": state.current_state,
        "data": state.data,
    }


def game_states_to_dict(states: Iterable[StateModel]) -> list[dict]:
    return [game_state_to_dict(state) for state in states]


def game_user_to_dict(user: UserModel) -> dict:
    return {
        "id": user.id,
        "id_tg": user.id_tg,
        "username_tg": user.username_tg,
    }


def game_users_to_dict(users: Iterable[UserModel]) -> list[dict]:
    return [game_user_to_dict(user) for user in users]


def game_player_to_dict(player: PlayerModel) -> dict:
    return {
        "id": player.id,
        "session_id": player.session_id,
        "is_active": player.is_active,
        "is_ready": player.is_ready,
        "is_captain": player.is_captain,
        "user_id": player.user_id,
    }


def game_players_to_dict(players: Iterable[PlayerModel]) -> list[dict]:
    return [game_player_to_dict(player) for player in players]
