import base64
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.admin.models import AdminModel
from app.base.base_accessor import BaseAccessor

if TYPE_CHECKING:
    from app import Application


class AdminAccessor(BaseAccessor):
    async def connect(self, app: "Application") -> None:
        import yaml
        with open('./config.yml', 'r') as f:
            raw_config = yaml.safe_load(f)
            admin_config = raw_config["admin"]

        password = self.app.config.admin.password
        encode_password = base64.b64encode(password.encode('utf-8')).decode('utf-8')

        await self.create_admin(admin_config["email"], encode_password)

    async def get_by_email(self, email: str) -> AdminModel | None:
        async with await self.app.database.get_session() as session:
            stmt = select(AdminModel).where(AdminModel.email == email)
            result = await session.execute(stmt)
            user = result.scalars().first()

        return user


    async def is_exist(self, email: str):
        if await self.get_by_email(email):
            return True
        return False

    async def create_admin(self, email: str, password: str) -> AdminModel:
        if await self.is_exist(email):
            return

        async with await self.app.database.get_session() as session:
            new_admin = AdminModel(email=email, password=password)
            session.add(new_admin)
            await session.commit()

