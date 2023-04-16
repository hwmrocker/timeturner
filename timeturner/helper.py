from typing import Iterator, cast

from pendulum import period
from pendulum.date import Date
from pendulum.datetime import DateTime


def iter_over_days(start: DateTime, end: DateTime) -> Iterator[Date]:
    end = end.subtract(microseconds=1)
    for dt in period(start.start_of("day"), end.start_of("day")).range("days"):
        yield cast(DateTime, dt).date()


def end_of(dt: DateTime, unit: str) -> DateTime:
    """Return the first possible moment of the next unit."""
    return dt.start_of(unit).add(**{f"{unit}s": 1})


def end_of_day(dt: DateTime) -> DateTime:
    """Return the first possible moment of the next day."""
    return dt.start_of("day").add(days=1)
