import json
import typing
from logging import getLogger

import aio_pika

from app.store.base import BaseAccessor

if typing.TYPE_CHECKING:
    from aio_pika.connection import Connection

    from app.web.app import Application


class RabbitMQAccessor(BaseAccessor):
    def __init__(self, app: "Application", *args, **kwargs):
        super().__init__(app, *args, **kwargs)
        self.connection: "Connection" | None = None
        self.logger = getLogger("rabbit_mq")

    async def connect(self, app: "Application"):
        self.connection = await aio_pika.connect(
            host=app.config.rabbit.host,
            port=app.config.rabbit.port,
            login=app.config.rabbit.user,
            password=app.config.rabbit.password,
        )

    async def send_message_in_update_for_game(self, update: dict):
        async with self.connection.channel() as channel:
            body_json = json.dumps(update)
            await channel.declare_queue("updates_for_game", durable=True)
            message = aio_pika.Message(
                body=body_json.encode("utf-8"),
                content_type="text/plain",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            )

            await channel.default_exchange.publish(
                message=message, routing_key="updates_for_game"
            )
            self.logger.info("Обновление отправленно")
