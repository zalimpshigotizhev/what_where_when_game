import typing

from app.bot.user.views import UserStatsListView

if typing.TYPE_CHECKING:
    from app.web.app import Application


def setup_routes(app: "Application"):
    app.router.add_view("/users.stats", UserStatsListView)
