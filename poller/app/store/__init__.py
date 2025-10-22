import typing

from app.store.rabbit.service_manager import RabbitMQAccessor
from app.store.tg_api.accessor import TelegramApiAccessor

if typing.TYPE_CHECKING:
    from app.web.app import Application


class Store:
    def __init__(self, app: "Application"):
        self.tg_api = TelegramApiAccessor(app)
        self.mq_manager = RabbitMQAccessor(app)


def setup_store(app: "Application"):
    app.store = Store(app)
