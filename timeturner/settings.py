from os import environ
from pathlib import Path
from typing import Any, Iterable, Literal

import tomlkit
from pendulum.date import Date
from pendulum.duration import Duration
from pydantic import BaseModel, BaseSettings, root_validator

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
    priority: int = 0
    track_work_time: bool = False
    track_work_time_passive: bool = False
    track_break_time: bool = False
    track_over_time: bool = False
    only_cover_work_days: bool = False

    @root_validator
    def check_tag_settings(cls, values):
        if values["track_work_time"] and values["track_work_time_passive"]:
            raise ValueError(
                "track_work_time and track_work_time_passive "
                "cannot be set at the same time"
            )
        if values["track_work_time"] and values["track_break_time"]:
            raise ValueError(
                "track_work_time and track_break_time cannot be set at the same time"
            )
        if values["track_work_time_passive"] and values["track_break_time"]:
            raise ValueError(
                "track_work_time_passive and track_break_time "
                "cannot be set at the same time"
            )
        if values["only_cover_work_days"] and not values["full_day"]:
            raise ValueError("only_cover_work_days can only be set if full_day is set")

        if values["track_over_time"] and not values["track_work_time"]:
            raise ValueError(
                "track_over_time can only be set if track_work_time is set"
            )

        if values["track_work_time"] and values["full_day"]:
            raise ValueError("track_work_time cannot be set if full_day is set")

        return values


class ReportSettings(BaseModel):
    output: Literal["json", "rich"] = "rich"
    holiday_tag: str = "holiday"
    passive_travel_tag: str = "travel"
    # vacation_tag: str = "vacation"
    # sick_tag: str = "sick"
    # sick_certified_tag: str = "sick-certified"
    worktime_per_weekday: dict[int, DurationSetting] = {
        0: DurationSetting(hours=8),
        1: DurationSetting(hours=8),
        2: DurationSetting(hours=8),
        3: DurationSetting(hours=8),
        4: DurationSetting(hours=8),
        5: DurationSetting(hours=0),
        6: DurationSetting(hours=0),
    }
    reset_default_work_time: bool = True
    tag_settings: dict[str, TagSettings] = {
        "holiday": TagSettings(
            name="holiday",
            full_day=True,
            priority=10,
        ),
        "sick-certified": TagSettings(
            name="sick-certified",
            full_day=True,
            priority=9,
        ),
        "vacation": TagSettings(
            name="vacation",
            full_day=True,
            priority=8,
            only_cover_work_days=True,
        ),
        "sick": TagSettings(
            name="sick",
            full_day=True,
            priority=7,
        ),
        "travel": TagSettings(
            name="travel",
            track_work_time_passive=True,
        ),
    }

    def is_work_day(self, day: Date) -> bool:
        weekday = day.weekday()
        if not self.worktime_per_weekday:
            return 0 <= weekday <= 4
        if weekday in self.worktime_per_weekday:
            return bool(self.worktime_per_weekday[weekday].duration)
        return False

    def has_full_day_tags(self, tags: Iterable[str]) -> bool:
        for tag in tags:
            if tag in self.tag_settings and self.tag_settings[tag].full_day:
                return True
        return False

    def get_tag(self, tag: str) -> TagSettings:
        if tag in self.tag_settings:
            return self.tag_settings[tag]
        return DefaultTagSettings(
            name=tag,
        )

    def get_highest_priority_tag(
        self, tags: Iterable[str], filter_full_day=False
    ) -> TagSettings:

        tag_settings = [self.get_tag(tag) for tag in tags]
        if filter_full_day:
            tag_settings = [tag for tag in tag_settings if tag.full_day]
        if tag_settings:
            return max(tag_settings, key=lambda tag: tag.priority)
        return DefaultTagSettings()

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
                f"tag_settings missing required tags: {', '.join(missing_tags)}"
            )
        # implement when writing tests for this
        # for tag_name, tag in values["tag_settings"].items():
        #     if isinstance(tag, dict):
        #         tag["name"] = tag_name
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


def DefaultTagSettings(name="no_tag"):

    return TagSettings(
        name=name,
        track_work_time=True,
        track_over_time=True,
    )
