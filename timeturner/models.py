from datetime import date, datetime
from enum import Enum, auto
from typing import Optional, cast

import pendulum
from pendulum.duration import Duration
from pendulum.time import Time
from pydantic import BaseModel, validator

from timeturner.helper import now_with_tz


class DayType(Enum):
    WORK = auto()
    HOLIDAY = auto()
    VACATION = auto()
    WEEKEND = auto()


class DailySummary(BaseModel):
    day: date
    day_type: DayType = DayType.WORK
    work_time: Duration = Duration()
    break_time: Duration = Duration()
    over_time: Duration = Duration()
    start: Optional[Time] = None
    end: Optional[Time] = None
    description: str | None = None
    by_tag: dict[str, Duration] = {}


class TimeSegment(BaseModel):
    start: datetime
    end: datetime | None = None
    passive: bool = False
    tags: list[str] = []
    description: str | None = None

    @validator("start")
    def parse_start(cls, value: str | datetime) -> datetime:
        if isinstance(value, datetime):
            return value
        new_value = datetime.fromisoformat(value)
        if isinstance(new_value, datetime):
            return new_value
        raise ValueError(f"Could not parse {value} as a datetime")

    @validator("end")
    def parse_end(cls, value: str | datetime | None) -> datetime | None:
        if value is None:
            return None
        return cls.parse_start(value)

    @validator("tags")
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
            duration = cast(Duration, now_with_tz() - self.start)
        else:
            duration = cast(Duration, self.end - self.start)

        return duration


class PensiveRow(TimeSegment):
    pk: int


class SegmentsByDay(BaseModel):
    day: date
    weekday: int
    segments: list[PensiveRow]
    summary: DailySummary
    tags: list[str]


class NewSegmentParams(BaseModel):
    start: datetime
    end: Optional[datetime]
    tags: list[str]
    description: str = ""
    passive: bool = False
