from __future__ import annotations

import datetime
from typing import Iterator, cast

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

import calendar


class Date(datetime.date):
    ...


class DateTime(datetime.datetime):
    def start_of(self, unit: str) -> DateTime:
        additional_delta = datetime.timedelta()
        if unit == "week":
            unit = "day"
            additional_delta = datetime.timedelta(days=-self.weekday())
        units_with_values = [
            ("year", None),
            ("month", 1),
            ("day", 1),
            ("hour", 0),
            ("minute", 0),
            ("second", 0),
            ("microsecond", 0),
        ]
        units = [u for u, _ in units_with_values]
        assert unit in units, f"Invalid unit: {unit!r}"
        index = units.index(unit)
        args = dict()
        for unit, new_value in units_with_values[index + 1 :]:
            args[unit] = new_value
        print(f"args: {args}")
        new_value = self.replace(**args)

        return new_value + additional_delta

    def add(self, weeks=0, **kwargs) -> DateTime:
        if weeks:
            kwargs["days"] = kwargs.get("days", 0) + weeks * 7
        return self + datetime.timedelta(**{k: -v for k, v in kwargs.items()})

    def subtract(self, **kwargs) -> DateTime:
        return self - datetime.timedelta(**{k: -v for k, v in kwargs.items()})


def iter_over_days(start: DateTime, end: DateTime) -> Iterator[Date]:
    end = end.subtract(microseconds=1)
    if end < start:
        return
    period = end.start_of("day") - start.start_of("day")
    for dt in period.range("days"):
        yield cast(DateTime, dt).date()


def end_of(dt: DateTime, unit: str) -> DateTime:
    """Return the first possible moment of the next unit."""
    if unit == "year":
        new_dt = dt.start_of("year")
        return new_dt.replace(year=new_dt.year + 1)
    if unit == "month":
        new_dt = dt.start_of("month")
        _, days_of_month = calendar.monthrange(new_dt.year, new_dt.month)
        return new_dt.add(days=days_of_month)
    return dt.start_of(unit).add(**{f"{unit}s": 1})


def end_of_day(dt: DateTime) -> DateTime:
    """Return the first possible moment of the next day."""
    return dt.start_of("day").add(days=1)


local_tz = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo


def now(tz=local_tz):
    return datetime.datetime.now(tz)
