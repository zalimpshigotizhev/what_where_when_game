import typing
from logging import getLogger

from app.store.tg_api.dataclasses import UpdateABC, MessageTG

if typing.TYPE_CHECKING:
    from app import Application


class BotManager:
    def __init__(self, app: "Application"):
        self.app = app
        self.bot = None
        self.logger = getLogger("handler")

    async def handle_updates(self, updates: list[UpdateABC]):
        for update in updates:
            if isinstance(update, MessageTG):
                await self.app.store.tg_api.send_message(
                    chat_id=update.chat.id_,
                    text=update.text
                )
