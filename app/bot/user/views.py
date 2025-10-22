from aiohttp_apispec import querystring_schema, response_schema

from app.bot.user.schemas import UserId, UserInfo
from app.web.app import View
from app.web.utils import json_response


class UserStatsListView(View):
    @querystring_schema(UserId)
    @response_schema(UserInfo)
    async def get(self):
        username_tg = self.request.query.get("username_tg") or None

        user_stats = await self.store.users.get_player_stats_by_username(
            username_tg
        )

        return json_response(data=UserInfo().dump(user_stats))
