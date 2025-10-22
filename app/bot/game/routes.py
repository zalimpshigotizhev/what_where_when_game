import typing

from app.bot.game.views import ActiveSessionListView, CompletedSessionListView

if typing.TYPE_CHECKING:
    from app.web.app import Application


def setup_routes(app: "Application"):
    app.router.add_view("/sessions.active", ActiveSessionListView)
    app.router.add_view("/sessions.completed", CompletedSessionListView)
