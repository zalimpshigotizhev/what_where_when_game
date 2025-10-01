from aiohttp.abc import StreamResponse
from aiohttp.web_exceptions import HTTPUnauthorized


class AuthRequiredMixin:
    async def _iter(self) -> StreamResponse:
        if self.request.admin is None:
            raise HTTPUnauthorized

        return await super()._iter()
