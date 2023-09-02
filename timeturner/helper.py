from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta, timezone
from typing import Iterator


def start_of(dt: datetime, unit: str) -> datetime:
    additional_delta = timedelta()
    if unit == "week":
        unit = "day"
        additional_delta = timedelta(days=-dt.weekday())
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
    new_value = dt.replace(**args)

    return new_value + additional_delta


def dt_add(dt: datetime, weeks=0, **kwargs) -> datetime:
    if weeks:
        kwargs["days"] = kwargs.get("days", 0) + weeks * 7
    print(f"dt: {dt!r}, kwargs: {kwargs!r}")
    return dt + timedelta(**{k: v for k, v in kwargs.items()})


def dt_subtract(dt: datetime, months=0, years=0, **kwargs) -> datetime:
    ret = dt - timedelta(**{k: v for k, v in kwargs.items()})
    new_month = ret.month
    new_year = ret.year
    if years:
        new_year = ret.year - years

    if months:
        year_delta = months // 12
        month_delta = months % 12

        new_month = ret.month - month_delta

        if new_month < 1:
            new_month = 12 + new_month
            year_delta += 1
        elif new_month > 12:
            new_month = new_month - 12
            year_delta -= 1

        new_year = new_year - year_delta

    return ret.replace(year=new_year, month=new_month)


def iter_over_days(start: datetime, end: datetime) -> Iterator[date]:
    print(f"start: {start!r}, end: {end!r}")
    end = dt_subtract(end, microseconds=1)
    if end < start:
        return
    print(f"start: {start!r}, end: {end!r}")

    next_day = start_of(start, "day")
    last_day = start_of(end, "day")
    idx = 0
    while next_day <= last_day:
        idx += 1
        if idx > 500:
            raise RuntimeError("Too many days")
        yield next_day.date()
        next_day = next_day + timedelta(days=1)


def end_of(dt: datetime, unit: str) -> datetime:
    """Return the first possible moment of the next unit."""
    if unit == "year":
        new_dt = start_of(dt, "year")
        return new_dt.replace(year=new_dt.year + 1)
    if unit == "month":
        new_dt = start_of(dt, "month")
        _, days_of_month = calendar.monthrange(new_dt.year, new_dt.month)
        return dt_add(new_dt, days=days_of_month)
    return dt_add(start_of(dt, unit), **{f"{unit}s": 1})


def end_of_day(dt: datetime) -> datetime:
    """Return the first possible moment of the next day."""
    return dt_add(start_of(dt, "day"), days=1)


local_tz = datetime.now(timezone.utc).astimezone().tzinfo


def now_with_tz(tz=local_tz):
    print(f"tz: {tz}")
    return datetime.now(tz)


def parse(date_string) -> datetime:
    """Parse a date string and adding the local timezone."""
    dt = datetime.fromisoformat(date_string)
    return dt.replace(tzinfo=local_tz)
