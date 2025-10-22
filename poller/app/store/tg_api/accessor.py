from typing import TYPE_CHECKING
from urllib.parse import urlencode, urljoin

from aiohttp import TCPConnector
from aiohttp.client import ClientSession

from app.base.base_accessor import BaseAccessor
from app.store.tg_api.poller import Poller

if TYPE_CHECKING:
    from app.web.app import Application

API_PATH = "https://api.telegram.org/"


class TelegramApiAccessor(BaseAccessor):
    def __init__(self, app: "Application", *args, **kwargs):
        super().__init__(app, *args, **kwargs)
        self.session: ClientSession | None = None
        self.poller: Poller | None = None
        self.timeout = 20
        self.offset = 0
        self.server: str = f"{API_PATH}bot{self.app.config.bot.token}/"

    async def connect(self, app: "Application") -> None:
        self.session = ClientSession(connector=TCPConnector(verify_ssl=False))

        self.poller = Poller(app.store)
        self.logger.info("start polling")
        self.poller.start()

    async def disconnect(self, app: "Application") -> None:
        if self.session:
            await self.session.close()

        if self.poller:
            await self.poller.stop()

    @staticmethod
    def _build_query(host: str, method: str, params: dict) -> str:
        return f"{urljoin(host, method)}?{urlencode(params)}"

    async def poll(self):
        async with self.session.get(
            self._build_query(
                host=self.server,
                method="getUpdates",
                params={"timeout": self.timeout, "offset": self.offset},
            )
        ) as response:
            result = await response.json()
            mq_manager = self.app.store.mq_manager
            if result.get("ok") and result.get("result"):
                self.logger.info(result)
                updates_dicts = result["result"]
                if updates_dicts:
                    self.offset = (
                        max(update["update_id"] for update in updates_dicts) + 1
                    )
                for update in updates_dicts:
                    await mq_manager.send_message_in_update_for_game(
                        update=update
                    )
