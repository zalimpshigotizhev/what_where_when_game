import typing
from logging import getLogger

from app.store.bot.gamebot.are_ready_state import (
    AreReadyNextRoundPlayersProcessGameBot,
)
from app.store.bot.gamebot.main_state import MainGameBot
from app.store.bot.gamebot.quest_disscution_state import (
    QuestionDiscussionProcessGameBot,
)
from app.store.bot.gamebot.verdict_captain_state import VerdictCaptain
from app.store.bot.gamebot.wait_answer_state import WaitAnswer
from app.store.bot.gamebot.wait_players_state import (
    WaitingPlayersProcessGameBot,
)
from app.store.rabbit.dataclasses import UpdateABC

if typing.TYPE_CHECKING:
    from app.web.app import Application


class BotManager:
    def __init__(self, app: "Application"):
        self.app = app
        self.states_handler = [
            MainGameBot(self.app),
            WaitingPlayersProcessGameBot(self.app),
            AreReadyNextRoundPlayersProcessGameBot(self.app),
            QuestionDiscussionProcessGameBot(self.app),
            VerdictCaptain(self.app),
            WaitAnswer(self.app),
        ]
        self.logger = getLogger("handler")
        self._handlers: list | None = None

        self._add_handlers_in_list()

    def _add_handlers_in_list(self):
        if self._handlers is None:
            self._handlers = []
            for state_handler in self.states_handler:
                self._handlers.extend(state_handler.handlers)
        return self._handlers

    async def handle_update(self, update: UpdateABC | None):
        if update is None:
            return

        curr_state = await self.app.store.fsm.get_state(chat_id=update.chat.id_)
        for handler in self._handlers:
            if callable(handler):
                result = await handler(update, curr_state)
                if result is not None:
                    break
