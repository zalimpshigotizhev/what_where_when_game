import json
from pprint import pprint
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode, urljoin

from aiohttp import TCPConnector
from aiohttp.client import ClientSession

from app.base.base_accessor import BaseAccessor
from app.store.bot.consts import MESSAGE_FOR_PRIVAT
from app.store.tg_api.dataclasses import CallbackTG, MessageTG
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
        updates_datas = []
        async with self.session.get(
            self._build_query(
                host=self.server,
                method="getUpdates",
                params={"timeout": self.timeout, "offset": self.offset},
            )
        ) as response:
            result = await response.json()
            self.logger.info(result)

            if result.get("ok") and result.get("result"):
                updates_dicts = result["result"]
                if updates_dicts:
                    self.offset = (
                        max(update["update_id"] for update in updates_dicts) + 1
                    )
                for update in updates_dicts:
                    if "message" in update:
                        message = MessageTG.from_dict(update["message"])
                        data: MessageTG = message

                        if message.is_command:
                            data = message.to_command()

                        if data.chat.type == "private":
                            await self.send_message(
                                chat_id=data.chat.id_, text=MESSAGE_FOR_PRIVAT
                            )
                            continue
                        updates_datas.append(data)

                    elif "callback_query" in update:
                        pprint(update["callback_query"])
                        callback = CallbackTG.from_dict(
                            update["callback_query"]
                        )
                        data = callback
                        updates_datas.append(data)
            await self.app.store.bots_manager.handle_updates(updates_datas)

    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: dict[str, Any] | None = None,
        parse_mode: str = "Markdown",
    ) -> MessageTG:
        """Отправляет СООБЩЕНИЕ в конкретный чат
        :param chat_id: int
        :param text: str
        :param reply_markup: dict
        :param parse_mode: str (По дефолту Markdown)
        :return:
        """
        params = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}

        if reply_markup:
            params["reply_markup"] = json.dumps(reply_markup)

        async with self.session.get(
            self._build_query(
                self.server,
                "sendMessage",
                params=params,
            )
        ) as response:
            data = await response.json()

            # self.logger.info(data)

            return MessageTG.from_dict(data.get("result"))

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: str = "",
        show_alert: bool = False,
        cache_time: int = 0,
    ) -> None:
        """Отправляет УВЕДОМЛЕНИЕ в конкретному пользователю"""
        params = {
            "callback_query_id": callback_query_id,
            "show_alert": show_alert,
            "cache_time": cache_time,
        }

        if text:
            params["text"] = text

        async with self.session.get(
            self._build_query(
                self.server,
                "answerCallbackQuery",
                params=params,
            )
        ) as response:
            data = await response.json()
            self.logger.info(data)

    async def delete_message(self, chat_id: int, message_id: int) -> None:
        """Отправляет УВЕДОМЛЕНИЕ в конкретному пользователю"""
        params = {"chat_id": chat_id, "message_id": message_id}

        async with self.session.get(
            self._build_query(
                self.server,
                "deleteMessage",
                params=params,
            )
        ) as response:
            data = await response.json()
            self.logger.info(data)

    async def delete_messages(self, chat_id: int, message_ids: list[int]):
        for message_id in message_ids:
            await self.delete_message(chat_id, message_id)
