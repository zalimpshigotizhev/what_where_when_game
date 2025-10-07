import typing

from app.store.bot.fsm import FSMContext
from app.store.database.database import Database
from app.store.game.accessor import SessionGameAccessor

if typing.TYPE_CHECKING:
    from app import Application


class Store:
    def __init__(self, app: "Application"):
        from app.store.admin.accessor import AdminAccessor
        from app.store.bot.manager import BotManager
        from app.store.quiz.accessor import QuizAccessor
        from app.store.tg_api.accessor import TelegramApiAccessor

        self.quizzes = QuizAccessor(app)
        self.admins = AdminAccessor(app)
        self.session_game = SessionGameAccessor(app)
        self.tg_api = TelegramApiAccessor(app)
        self.bots_manager = BotManager(app)
        self.fsm = FSMContext(app)


def setup_store(app: "Application"):
    app.database = Database(app)
    app.on_startup.append(app.database.connect)
    app.on_cleanup.append(app.database.disconnect)
    app.store = Store(app)
