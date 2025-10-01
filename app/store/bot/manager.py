import typing
from logging import getLogger

from app.store.tg_api.dataclasses import Message, Update

if typing.TYPE_CHECKING:
    from app import Application


class BotManager:
    def __init__(self, app: "Application"):
        self.app = app
        self.bot = None
        self.logger = getLogger("handler")

    async def handle_updates(self, updates: list[Update]):
        for update in updates:
            await self.app.store.vk_api.send_message(
                Message(
                    user_id=update.object.message.from_id,
                    text="Привет!",
                )
            )
