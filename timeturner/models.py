from typing import Optional

from pendulum.date import Date
from pendulum.datetime import DateTime
from pendulum.duration import Duration
from pendulum.time import Time
from pydantic import BaseModel

from timeturner.db import PensiveRow


class DailySummary(BaseModel):
    work_time: Duration = Duration()
    break_time: Duration = Duration()
    start: Optional[Time] = None
    end: Optional[Time] = None
    by_tag: dict[str, Duration] = {}


class SegmentsByDay(BaseModel):
    day: Date
    weekday: int
    segments: list[PensiveRow]
    summary: DailySummary


class NewSegmentParams(BaseModel):
    start: DateTime
    end: Optional[DateTime]
    tags: list[str]
    description: str = ""
    passive: bool = False
