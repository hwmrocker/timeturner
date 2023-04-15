from os import environ
from pathlib import Path
from typing import Any, Literal

import tomlkit
from pendulum.duration import Duration
from pydantic import BaseModel, BaseSettings, root_validator, validator

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


class DurationSetting(BaseModel):
    hours: int = 0
    minutes: int = 0

    @property
    def duration(self) -> Duration:
        return Duration(
            hours=self.hours,
            minutes=self.minutes,
        )


class TagSettings(BaseModel):
    name: str
    full_day: bool = False
    work_day: bool = False
    track_work_time: bool = False
    track_work_time_passive: bool = False
    track_break_time: bool = False
    track_over_time: bool = False


class ReportSettings(BaseModel):
    output: Literal["json", "rich"] = "rich"
    holiday_tag: str = "holiday"
    passive_travel_tag: str = "travel"
    # vacation_tag: str = "vacation"
    # sick_tag: str = "sick"
    # sick_certified_tag: str = "sick-certified"
    reset_default_work_time: bool = True
    tag_settings: dict[str, TagSettings] = {
        "holiday": TagSettings(
            name="holiday",
            full_day=True,
        ),
        "vacation": TagSettings(
            name="vacation",
            full_day=True,
        ),
        "sick": TagSettings(
            name="sick",
            full_day=True,
        ),
        "travel": TagSettings(
            name="travel",
            track_work_time_passive=True,
        ),
    }

    @root_validator
    def validate_tag_settings(cls, values):

        avaliable_tags = set(values["tag_settings"].keys())
        required_tags = {
            values["holiday_tag"],
            values["passive_travel_tag"],
        }
        missing_tags = required_tags - avaliable_tags
        if missing_tags:
            raise ValueError(
                f"tag_settings missing required tag definition: {', '.join(missing_tags)}"
            )
        return values


class TimeTurnerSettings(Settings):
    database: DatabaseSettings = DatabaseSettings()
    report: ReportSettings = ReportSettings()

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
