from os import environ
from pathlib import Path
from typing import Any, Literal

import tomlkit
from pydantic import BaseModel, BaseSettings

from timeturner import __COMMIT__, __VERSION__
from timeturner.db import DatabaseConnection

DEFAULT_CONFIG_HOME = (
    Path.home() / environ.get("XDG_CONFIG_HOME", ".config") / "timeturner"
)


class Settings(BaseSettings):
    config_file: str = "config.toml"
    config_home: Path = DEFAULT_CONFIG_HOME

    @property
    def config_path(self) -> Path:
        return self.config_home / self.config_file

    class Config:
        env_file_encoding = "utf-8"
        env_prefix = "timeturner_"


config_settings = Settings()


def load_config_file(settings: BaseSettings) -> dict[str, Any]:
    encoding = settings.__config__.env_file_encoding
    config_file = config_settings.config_path
    if not config_file.exists():
        return {}
    return tomlkit.loads(config_file.read_text(encoding))


class DatabaseSettings(BaseModel):
    file: str = "timeturner.db"
    home: Path = config_settings.config_home
    table_name: str = "pensieve"

    @property
    def database_path(self) -> Path:
        return self.home / self.file

    @property
    def connection(self) -> DatabaseConnection:
        self.home.mkdir(parents=True, exist_ok=True)
        return DatabaseConnection(
            str(self.database_path.resolve()),
            table_name=self.table_name,
        )


class TimeTurnerSettings(Settings):
    database: DatabaseSettings = DatabaseSettings()
    output: Literal["json", "rich"] = "rich"

    version: str = __VERSION__
    commit: str = __COMMIT__

    class Config:
        env_file_encoding = "utf-8"
        env_prefix = "timeturner_"
        env_nested_delimiter = "__"

        @classmethod
        def customise_sources(
            cls,
            init_settings,
            env_settings,
            file_secret_settings,
        ):
            del file_secret_settings
            return (
                init_settings,
                env_settings,
                load_config_file,
            )
