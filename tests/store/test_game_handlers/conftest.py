import pytest

from app.store.bot.gamebot.base import BotBase
from app.store.tg_api.dataclasses import CallbackTG, MessageTG


@pytest.fixture
def bot_base(mock_app):
    """Создает экземпляр BotBase для тестирования"""
    return BotBase(mock_app)


@pytest.fixture
def chat_id():
    return 123


@pytest.fixture
def session_id():
    return 321


@pytest.fixture
def session_game(chat_id, session_id):
    """Создает экземпляр BotBase для тестирования"""
    from app.bot.game.models import (
        SessionModel,
        StatusSession,
    )

    return SessionModel(
        id=session_id,
        chat_id=chat_id,
        status=StatusSession.PROCESSING,
        current_round_id=None,
    )


@pytest.fixture
def callback(mock_app, chat_id):
    return CallbackTG.from_dict(
        {
            "chat_instance": "526193150226325798",
            "data": "start_game",
            "from": {
                "first_name": "х",
                "id": 1278888559,
                "is_bot": False,
                "is_premium": True,
                "language_code": "ru",
                "username": "courvuisier",
            },
            "id": "5492784537346795564",
            "message": {
                "chat": {"id": 123, "title": "т", "type": "supergroup"},
                "date": 1760457959,
                "from": {
                    "first_name": "Что? Где? Когда?",
                    "id": 7997238478,
                    "is_bot": True,
                    "username": "quiz_zalim_bot",
                },
                "message_id": 41,
                "reply_markup": {
                    "inline_keyboard": [
                        [
                            {
                                "callback_data": "start_game",
                                "text": "🎮 Начать игру",
                            }
                        ],
                        [
                            {
                                "callback_data": "show_rules",
                                "text": "📋 Правила",
                            },
                            {
                                "callback_data": "show_rating",
                                "text": "⭐ Рейтинг",
                            },
                        ],
                    ]
                },
                "text": "Добро пожаловать в игру! "
                "Используйте кнопки ниже для "
                "управления.",
            },
        }
    )


@pytest.fixture
def message(mock_app, chat_id):
    return MessageTG.from_dict(
        {
            "message_id": 246,
            "from": {
                "id": 1278888559,
                "is_bot": False,
                "first_name": "х",
                "username": "courvuisier",
                "language_code": "ru",
                "is_premium": True,
            },
            "chat": {"id": chat_id, "title": "т", "type": "supergroup"},
            "date": 1760564201,
            "text": "naha",
        }
    )


@pytest.fixture
def player1(session_game):
    from app.bot.game.models import PlayerModel
    from app.bot.user.models import UserModel

    return PlayerModel(
        id=1,
        session_id=session_game.id,
        is_active=True,
        is_ready=True,
        is_captain=True,
        user=UserModel(id=1, username_tg="courvusadaisier", id_tg=1),
    )


@pytest.fixture
def player2(session_game):
    from app.bot.game.models import PlayerModel
    from app.bot.user.models import UserModel

    return PlayerModel(
        id=1,
        session_id=session_game.id,
        is_active=True,
        is_ready=True,
        is_captain=False,
        user=UserModel(id=1, username_tg="courvusadaisier", id_tg=2),
    )


@pytest.fixture
def player3(session_game):
    from app.bot.game.models import PlayerModel
    from app.bot.user.models import UserModel

    return PlayerModel(
        id=1,
        session_id=session_game.id,
        is_active=True,
        is_ready=True,
        is_captain=False,
        user=UserModel(id=1, username_tg="courvusadaisier", id_tg=3),
    )


@pytest.fixture
def player4(session_game):
    from app.bot.game.models import PlayerModel
    from app.bot.user.models import UserModel

    return PlayerModel(
        id=1,
        session_id=session_game.id,
        is_active=True,
        is_ready=True,
        is_captain=False,
        user=UserModel(id=1, username_tg="courvusadaisier", id_tg=4),
    )


@pytest.fixture
def player5(session_game):
    from app.bot.game.models import PlayerModel
    from app.bot.user.models import UserModel

    return PlayerModel(
        id=1,
        session_id=session_game.id,
        is_active=True,
        is_ready=True,
        is_captain=False,
        user=UserModel(id=1, username_tg="courvusadaisier", id_tg=5),
    )


@pytest.fixture
def player6(session_game):
    from app.bot.game.models import PlayerModel
    from app.bot.user.models import UserModel

    return PlayerModel(
        id=1,
        session_id=session_game.id,
        is_active=True,
        is_ready=True,
        is_captain=False,
        user=UserModel(id=1, username_tg="courvusadaisier", id_tg=6),
    )


@pytest.fixture
def player7(session_game):
    from app.bot.game.models import PlayerModel
    from app.bot.user.models import UserModel

    return PlayerModel(
        id=1,
        session_id=session_game.id,
        is_active=False,
        is_ready=False,
        is_captain=False,
        user=UserModel(id=1, username_tg="courvusadaisier", id_tg=7),
    )


@pytest.fixture
def full_players(
    player1,
    player2,
    player3,
    player4,
    player5,
    player6,
):
    return [
        player1,
        player2,
        player3,
        player4,
        player5,
        player6,
    ]
