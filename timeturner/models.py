from datetime import datetime
from enum import Enum, auto
from typing import Optional, cast

import pendulum
from pendulum.date import Date
from pendulum.datetime import DateTime
from pendulum.duration import Duration
from pendulum.parser import parse
from pendulum.time import Time
from pydantic import BaseModel, ConfigDict, field_validator


class DayType(Enum):
    WORK = auto()
    HOLIDAY = auto()
    VACATION = auto()
    WEEKEND = auto()


class DailySummary(BaseModel):
    day: Date
    day_type: DayType = DayType.WORK
    work_time: Duration = Duration()
    break_time: Duration = Duration()
    over_time: Duration = Duration()
    start: Optional[Time] = None
    end: Optional[Time] = None
    description: str | None = None
    by_tag: dict[str, Duration] = {}

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )


class TimeSegment(BaseModel):
    start: DateTime
    end: DateTime | None = None
    passive: bool = False
    tags: list[str] = []
    description: str | None = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    @field_validator("start")
    @classmethod
    def parse_start(cls, value: str | datetime | DateTime) -> DateTime:
        if isinstance(value, DateTime):
            return value
        if isinstance(value, datetime):
            value = str(value)
        new_value = parse(value)
        if isinstance(new_value, DateTime):
            return new_value
        raise ValueError(f"Could not parse {value} as a datetime")

    @field_validator("end")
    @classmethod
    def parse_end(cls, value: str | datetime | DateTime | None) -> DateTime | None:
        if value is None:
            return None
        return cls.parse_start(value)

    @field_validator("tags")
    @classmethod
    def parse_tags(cls, value: str | list[str] | None) -> list[str] | None:
        if not value:
            # we want to return a new empty list, not reuse the default empty list
            return []
        if isinstance(value, str):
            return value.split(",")
        if isinstance(value, list):
            return value
        raise ValueError(f"Could not parse {value} as a list of tags")

    @property
    def duration(self) -> Duration:
        if self.end is None:
            duration = cast(Duration, pendulum.now() - self.start)
        else:
            duration = cast(Duration, self.end - self.start)

        return duration


class PensiveRow(TimeSegment):
    pk: int


class SegmentsByDay(BaseModel):
    day: Date
    weekday: int
    segments: list[PensiveRow]
    summary: DailySummary
    tags: list[str]

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )


class NewSegmentParams(BaseModel):
    start: DateTime
    end: Optional[DateTime] = None
    tags: list[str]
    description: str = ""
    passive: bool = False

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )
