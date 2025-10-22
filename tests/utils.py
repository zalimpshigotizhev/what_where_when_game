from collections.abc import Iterable

from app.bot.game.models import (
    PlayerModel,
    RoundModel,
    SessionModel,
    StateModel,
)
from app.bot.user.models import UserModel
from app.quiz.models import AnswerModel, QuestionModel, ThemeModel


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


def game_round_to_dict(round: RoundModel) -> dict:
    return {
        "id": round.id,
        "session_id": round.session_id,
        "is_active": round.is_active,
        "is_correct_answer": round.is_correct_answer,
        "question_id": round.question_id,
        "answer_player_id": round.answer_player_id,
    }


def game_rounds_to_dict(rounds: Iterable[RoundModel]) -> list[dict]:
    return [game_round_to_dict(roundd) for roundd in rounds]


def theme_to_dict(theme: ThemeModel) -> dict:
    return {
        "id": theme.id,
        "title": theme.title,
    }


def themes_to_dict(themes: Iterable[ThemeModel]) -> list[dict]:
    return [theme_to_dict(theme) for theme in themes]


def question_to_dict(question: QuestionModel) -> dict:
    return {
        "id": question.id,
        "title": question.title,
        "theme_id": question.theme_id,
    }


def questions_to_dict(questions: Iterable[QuestionModel]) -> list[dict]:
    return [question_to_dict(question) for question in questions]


def answer_to_dict(answer: AnswerModel) -> dict:
    return {
        "id": answer.id,
        "title": answer.title,
        "description": answer.description,
        "question_id": answer.question_id,
    }


def answers_to_dict(answers: Iterable[AnswerModel]) -> list[dict]:
    return [answer_to_dict(answer) for answer in answers]
