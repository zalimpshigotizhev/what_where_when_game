import csv
from logging import getLogger

import yaml
from sqlalchemy import MetaData, Table, insert
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def get_data_by_csv(file_csv):
    with open(file_csv, "r", encoding="utf-8") as file:
        normalize_list = []
        reader = csv.DictReader(file)
        for data in reader:
            if data.get("id") is not None:
                data["id"] = int(data.get("id"))

            if data.get("theme_id") is not None:
                data["theme_id"] = int(data.get("theme_id"))

            if data.get("question_id") is not None:
                data["question_id"] = int(data.get("question_id"))

            normalize_list.append(data)
        return normalize_list


def get_url_for_alembic(url_config: str, debug=False) -> str:
    with open(url_config, "r") as f:
        raw_config = yaml.safe_load(f)

    db_config = raw_config.get("database")
    user = db_config.get("user")
    password = db_config.get("password")
    host = db_config.get("host")
    port = db_config.get("port")
    database = db_config.get("database")

    if debug:
        host = "localhost"
    return (
        f"postgresql+asyncpg://"
        f"{user}:{password}@"
        f"{host}:{port}"
        f"/{database}"
    )


def get_async_engine(config_url: str, debug: bool = False):
    db_url = get_url_for_alembic(url_config=config_url, debug=debug)
    return create_async_engine(db_url)


async def add_data_for_table(async_engine, table_name: str, data_url: str):
    async_session = async_sessionmaker(
        bind=async_engine, expire_on_commit=False
    )
    data = get_data_by_csv(file_csv=data_url)
    async with async_session() as session:
        metadata = MetaData()
        table_obj = await session.run_sync(
            lambda sync_session: Table(
                table_name, metadata, autoload_with=sync_session.connection()
            )
        )
        stmt = insert(table_obj).values(data)
        getLogger("ADD_DATA_IN_DB").info(
            "added %s rows for '%s' status: ok", str(len(data)), table_name
        )
        await session.execute(stmt)
        await session.commit()
