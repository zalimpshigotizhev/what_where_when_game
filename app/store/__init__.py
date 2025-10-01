import typing

from app import Database

if typing.TYPE_CHECKING:
    from app import Application


class Store:
    def __init__(self, app: "Application"):
        from app import AdminAccessor
        from app import BotManager
        from app import QuizAccessor
        from app import VkApiAccessor

        self.quizzes = QuizAccessor(app)
        self.admins = AdminAccessor(app)
        self.vk_api = VkApiAccessor(app)
        self.bots_manager = BotManager(app)



def setup_store(app: "Application"):
    app.database = Database(app)
    app.on_startup.append(app.database.connect)
    app.on_cleanup.append(app.database.disconnect)
    app.store = Store(app)
