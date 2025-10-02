import base64
import json

from aiohttp import web
from aiohttp_apispec import request_schema, response_schema

from app.admin.schemes import AdminSchema
from app.web.app import View
from app.web.middlewares import HTTP_ERROR_CODES
from app.web.utils import (
    decode_data,
    encode_data,
    error_json_response,
    json_response,
)


class AdminLoginView(View):
    @request_schema(AdminSchema)
    @response_schema(AdminSchema, 200)
    async def post(self):
        data = self.data
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return web.Response(
                text="Email and password are required", status=400
            )

        admin = await self.store.admins.get_by_email(email=email)
        if not admin:
            return error_json_response(
                http_status=403, status=HTTP_ERROR_CODES[403]
            )

        decode_admin_password = base64.b64decode(
            admin.password.encode("utf-8")
        ).decode("utf-8")

        if admin and decode_admin_password == password:
            response = json_response(
                data={"id": admin.id, "email": admin.email}
            )
            data = {"id": admin.id, "email": admin.email, "is_admin": True}
            data_for_cookie = encode_data(
                json.dumps(data), self.request.app.config.session.key
            )
            response.set_cookie(
                name="session_id",
                value=data_for_cookie,
                max_age=3600,
                httponly=False,
                secure=False,
                samesite="Lax",
            )
            return response

        return error_json_response(
            http_status=403, status=HTTP_ERROR_CODES[403]
        )


class AdminCurrentView(View):
    @response_schema(AdminSchema, 200)
    async def get(self):
        auth_cookie = self.request.cookies.get("session_id")

        if not auth_cookie:
            return error_json_response(
                http_status=401, status=HTTP_ERROR_CODES[401]
            )

        data_for_cookie = json.loads(
            decode_data(auth_cookie, self.request.app.config.session.key)
        )

        current_admin = await self.store.admins.get_by_email(
            data_for_cookie.get("email")
        )

        if data_for_cookie and data_for_cookie.get("id") == current_admin.id:
            return json_response(
                data={"id": current_admin.id, "email": current_admin.email}
            )

        return error_json_response(
            http_status=401, status=HTTP_ERROR_CODES[401]
        )
