import typing

from app.store.database.database import Database
from app.store.fsm.fsm import FSMContext
from app.store.game.player_accessor import PlayerAccessor
from app.store.game.round_accessor import RoundAccessor
from app.store.game.session_accessor import GameSessionAccessor
from app.store.game.user_accessor import UserAccessor
from app.store.rabbit.service_manager import RabbitMQAccessor
from app.store.timer.timer_manager import TimerManager

if typing.TYPE_CHECKING:
    from app.web.app import Application


class Store:
    def __init__(self, app: "Application"):
        from app.store.admin.accessor import AdminAccessor
        from app.store.bot.manager import BotManager
        from app.store.quiz.accessor import QuizAccessor
        from app.store.tg_api.accessor import TelegramApiAccessor

        self.quizzes = QuizAccessor(app)
        self.admins = AdminAccessor(app)

        # Добавленные ассесоры
        self.game_session = GameSessionAccessor(app)
        self.users = UserAccessor(app)
        self.players = PlayerAccessor(app)
        self.rounds = RoundAccessor(app)

        # Таймер
        self.timer_manager = TimerManager(app)
        self.rabbit = RabbitMQAccessor(app)

        self.tg_api = TelegramApiAccessor(app)
        self.bots_manager = BotManager(app)
        self.fsm = FSMContext(app)


def setup_store(app: "Application"):
    app.database = Database(app)
    app.on_startup.append(app.database.connect)
    app.on_cleanup.append(app.database.disconnect)
    app.store = Store(app)
