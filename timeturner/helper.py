from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta, timezone
from typing import Iterator, Union, overload


def start_of(dt: datetime | date, unit: str) -> datetime:
    if isinstance(dt, date) and not isinstance(dt, datetime):
        # Convert date to datetime at the start of the day
        dt = datetime.combine(dt, datetime.min.time()).astimezone()

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
    new_value = dt.replace(**args)

    return (new_value + additional_delta).replace(tzinfo=None).astimezone()


@overload
def dt_add(dt: datetime, weeks=0, **kwargs) -> datetime: ...
@overload
def dt_add(dt: date, weeks=0, **kwargs) -> date: ...


def dt_add(dt: Union[datetime, date], weeks=0, **kwargs) -> Union[datetime, date]:
    if weeks:
        kwargs["days"] = kwargs.get("days", 0) + weeks * 7
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

        new_year = new_year - year_delta

    # we want to ensure that the new date uses a valid timezone for this datetime. E.g. when we substrach a month,
    # we don't want to substract the exact hours, but want the datetime object with the same time but the replaced date.
    return ret.replace(year=new_year, month=new_month, tzinfo=None).astimezone()


def iter_over_days(start: datetime, end: datetime) -> Iterator[date]:
    end = end - timedelta(microseconds=1)
    # dt_subtract(end, microseconds=1)
    if end < start:
        return

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
        return new_dt.replace(year=new_dt.year + 1, tzinfo=None).astimezone()
    if unit == "month":
        new_dt = start_of(dt, "month")
        _, days_of_month = calendar.monthrange(new_dt.year, new_dt.month)
        return dt_add(new_dt, days=days_of_month)
    return dt_add(start_of(dt, unit), **{f"{unit}s": 1})


def end_of_day(dt: datetime | date) -> datetime:
    """Return the first possible moment of the next day."""
    if isinstance(dt, date) and not isinstance(dt, datetime):
        # Convert date to datetime at the start of the day
        dt = datetime.combine(dt, datetime.min.time()).astimezone()
    return dt_add(start_of(dt, "day"), days=1)


local_tz = datetime.now(timezone.utc).astimezone().tzinfo


def now_with_tz(tz=local_tz):
    return datetime.now(tz)


def parse(date_string) -> datetime:
    """Parse a date string and adding the local timezone."""
    dt = datetime.fromisoformat(date_string)
    return dt.astimezone()


def get_tz_offset(dt: datetime) -> int:
    offset_delta = dt.utcoffset()
    if offset_delta is None:
        raise ValueError("The datetime object must be timezone-aware.")
    return -int(offset_delta.total_seconds() // (60 * 60))
