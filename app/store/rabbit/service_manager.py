import json
import typing
from logging import getLogger

import aio_pika
from aio_pika.connection import Connection

from app.base.base_accessor import BaseAccessor
from app.store.rabbit.dataclasses import CallbackTG, MessageTG
from app.store.rabbit.rabbit_listener import RabbitMQListener

if typing.TYPE_CHECKING:
    from app.web.app import Application


class RabbitMQAccessor(BaseAccessor):
    def __init__(self, app: "Application", *args, **kwargs):
        super().__init__(app, *args, **kwargs)
        self.connection: Connection | None = None
        self.logger = getLogger("rabbit_mq")

    async def connect(self, app: "Application"):
        self.connection = await aio_pika.connect(
            host=app.config.rabbit.host,
            port=app.config.rabbit.port,
            login=app.config.rabbit.user,
            password=app.config.rabbit.password,
        )
        self.rbmq_listener = RabbitMQListener(app.store)
        self.logger.info("Начинаем слушать сообщения")
        self.rbmq_listener.start()

    async def disconnect(self, app: "Application"):
        if self.connection:
            await self.connection.close()

        if self.rbmq_listener:
            await self.rbmq_listener.stop()

    async def wait_updates_for_game(self):
        async with self.connection.channel() as ch:
            await ch.set_qos(5)

            queue = await ch.declare_queue("updates_for_game", durable=True)
            async for message in queue.iterator():
                async with message.process():
                    json_obj = message.body.decode()
                    await self.handle_update(json_obj)

    async def handle_update(self, update_json: str):
        update = json.loads(update_json)
        data = None
        if "message" in update:
            message = MessageTG.from_dict(update["message"])
            data = message

            if message.is_command:
                data = message.to_command()

            # if data.chat.type == "private":
            #     await self.send_message(
            #         chat_id=data.chat.id_, text=MESSAGE_FOR_PRIVAT
            #     )
            #     continue

        elif "callback_query" in update:
            callback = CallbackTG.from_dict(update["callback_query"])
            data = callback

        await self.app.store.bots_manager.handle_update(data)
