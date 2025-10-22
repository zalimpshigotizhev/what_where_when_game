import typing
from dataclasses import dataclass

import yaml

if typing.TYPE_CHECKING:
    from poller.app.web.app import Application


@dataclass
class BotConfig:
    token: str
    group_id: int


@dataclass
class RabbitConfig:
    host: str
    port: int
    user: str
    password: str


@dataclass
class Config:
    bot: BotConfig | None = None
    rabbit: RabbitConfig | None = None


def get_config_to_dict(config_path: str) -> dict:
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def setup_config(app: "Application", config_path: str):
    raw_config = get_config_to_dict(config_path=config_path)
    app.config = Config(
        bot=BotConfig(
            token=raw_config["bot"]["token"],
            group_id=raw_config["bot"]["group_id"],
        ),
        rabbit=RabbitConfig(**raw_config["rabbit"]),
    )
