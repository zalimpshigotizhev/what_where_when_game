from aiohttp_apispec import querystring_schema, response_schema

from app.bot.game.schemas import ChatIdSchema, SessionListSchema, SessionSchema
from app.web.app import View
from app.web.utils import json_response


class ActiveSessionListView(View):
    @response_schema(SessionListSchema)
    async def get(self):
        active_sessions = await self.store.game_session.get_active_sessions()

        return json_response(
            data={
                "active_sessions": [
                    SessionSchema().dump(session) for session in active_sessions
                ]
            }
        )


class CompletedSessionListView(View):
    @querystring_schema(ChatIdSchema)
    @response_schema(SessionListSchema)
    async def get(self):
        chat_id = self.request.query.get("chat_id") or None

        completed_sessions = (
            await self.store.game_session.get_completed_sessions(chat_id)
        )

        return json_response(
            data={
                "active_sessions": [
                    SessionSchema().dump(session)
                    for session in completed_sessions
                ]
            }
        )
