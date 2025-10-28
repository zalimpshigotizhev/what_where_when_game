import json
from logging import getLogger
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode, urljoin

from aiohttp import TCPConnector
from aiohttp.client import ClientSession

from app.base.base_accessor import BaseAccessor
from app.store.rabbit.dataclasses import MessageTG

if TYPE_CHECKING:
    from app.web.app import Application

API_PATH = "https://api.telegram.org/"


class TelegramApiAccessor(BaseAccessor):
    def __init__(self, app: "Application", *args, **kwargs):
        super().__init__(app, *args, **kwargs)
        self.session: ClientSession | None = None
        self.server: str = f"{API_PATH}bot{self.app.config.bot.token}/"
        self.logger = getLogger("TelegramApiAccessor")

    async def connect(self, app: "Application") -> None:
        self.session = ClientSession(connector=TCPConnector(verify_ssl=False))

    async def disconnect(self, app: "Application") -> None:
        if self.session:
            await self.session.close()

    @staticmethod
    def _build_query(host: str, method: str, params: dict) -> str:
        return f"{urljoin(host, method)}?{urlencode(params)}"

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
        logger = getLogger("send_message_tg_api")
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
            result = await response.json()
            if response.status == 200 and result.get("ok"):
                logger.info("Message send successfully: %s", result)
            else:
                logger.error(
                    "Failed to send message. " "Status: %d, " "Response: %s",
                    response.status,
                    result,
                )

            return MessageTG.from_dict(result.get("result"))

    async def edit_message(
        self,
        chat_id: int,
        message_id: int,
        new_text: str,
        reply_markup: dict[str, Any] | None = None,
        parse_mode: str = "Markdown",
    ):
        """Отправляет СООБЩЕНИЕ в конкретный чат
        :param chat_id: int
        :param text: str
        :param reply_markup: dict
        :param parse_mode: str (По дефолту Markdown)
        :return:
        """
        logger = getLogger("edit_message_tg_api")
        params = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": new_text,
            "parse_mode": parse_mode,
        }

        if reply_markup:
            params["reply_markup"] = json.dumps(reply_markup)

        async with self.session.get(
            self._build_query(
                self.server,
                "editMessageText",
                params=params,
            )
        ) as response:
            result = await response.json()
            if response.status == 200 and result.get("ok"):
                logger.info("Message edited successfully: %s", result)
            else:
                logger.error(
                    "Failed to edit message. " "Status: %d, " "Response: %s",
                    response.status,
                    result,
                )

    async def pin_message(
        self, chat_id: int, message_id: int, unpin: bool = False
    ):
        """Отправляет СООБЩЕНИЕ в конкретный чат
        :param chat_id: int
        :return:
        """
        logger = getLogger("pin_or_unpin_message_tg_api")

        params = {
            "chat_id": chat_id,
            "message_id": message_id,
            "unpin": unpin,
        }

        async with self.session.get(
            self._build_query(
                self.server,
                "pinChatMessage",
                params=params,
            )
        ) as response:
            result = await response.json()
            if response.status == 200 and result.get("ok"):
                logger.info("Message pin or unpin successfully: %s", result)
            else:
                logger.error(
                    "Failed to pin or unpin message. "
                    "Status: %d, "
                    "Response: %s",
                    response.status,
                    result,
                )

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: str = "",
        show_alert: bool = False,
        cache_time: int = 0,
    ) -> None:
        """Отправляет УВЕДОМЛЕНИЕ в конкретному пользователю"""
        logger = getLogger("answer_message_tg_api")

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
            result = await response.json()
            if response.status == 200 and result.get("ok"):
                logger.info("Message answer successfully: %s", result)
            else:
                logger.error(
                    "Failed to answer message. " "Status: %d, " "Response: %s",
                    response.status,
                    result,
                )

    async def delete_message(self, chat_id: int, message_id: int) -> None:
        """Отправляет УВЕДОМЛЕНИЕ в конкретному пользователю"""
        logger = getLogger("delete_message_tg_api")

        params = {"chat_id": chat_id, "message_id": message_id}

        async with self.session.get(
            self._build_query(
                self.server,
                "deleteMessage",
                params=params,
            )
        ) as response:
            result = await response.json()
            if response.status == 200 and result.get("ok"):
                logger.info("Message delete successfully: %s", result)
            else:
                logger.error(
                    "Failed to delete message. " "Status: %d, " "Response: %s",
                    response.status,
                    result,
                )

    async def delete_messages(self, chat_id: int, message_ids: list[int]):
        for message_id in message_ids:
            await self.delete_message(chat_id, message_id)
