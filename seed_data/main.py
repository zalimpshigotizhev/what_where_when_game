import asyncio
import logging

from seeds.quiz_seed import add_data_for_table, get_async_engine

url_for_themes = "./data/themes.csv"
url_for_quests = "./data/quests.csv"
url_for_answers = "./data/answers.csv"


async def main():
    logging.basicConfig(level=logging.INFO)

    async_engine = get_async_engine(config_url="../config.yml", debug=True)

    await add_data_for_table(
        table_name="themes",
        data_url=url_for_themes,
        async_engine=async_engine,
    )
    await add_data_for_table(
        table_name="questions",
        data_url=url_for_quests,
        async_engine=async_engine,
    )
    await add_data_for_table(
        table_name="answers",
        data_url=url_for_answers,
        async_engine=async_engine,
    )


if __name__ == "__main__":
    asyncio.run(main())
