import base64
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.admin.models import AdminModel
from app.base.base_accessor import BaseAccessor

if TYPE_CHECKING:
    from app import Application


class AdminAccessor(BaseAccessor):
    async def connect(self, app: "Application") -> None:
        email = self.app.config.admin.email
        password = self.app.config.admin.password
        encode_password = base64.b64encode(
            password.encode('utf-8')
        ).decode('utf-8')

        await self.create_admin(email, encode_password)

    async def get_by_email(self, email: str) -> AdminModel | None:
        async with await self.app.database.get_session() as session:
            stmt = select(AdminModel).where(AdminModel.email == email)
            result = await session.execute(stmt)
        return result.scalars().first()

    async def is_exist(self, email: str) -> bool:
        return bool(await self.get_by_email(email))

    async def create_admin(
            self, email: str, password: str
    ) -> AdminModel | None:
        if await self.is_exist(email):
            return

        async with await self.app.database.get_session() as session:
            new_admin = AdminModel(email=email, password=password)
            session.add(new_admin)
            await session.commit()

