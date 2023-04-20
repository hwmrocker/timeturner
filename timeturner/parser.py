import re

# from pendulum.tz.timezone import Timezone
from enum import Enum
from typing import Any, TypedDict

import pendulum
from pendulum.datetime import DateTime
from pendulum.duration import Duration

from timeturner.helper import end_of, end_of_day
from timeturner.models import NewSegmentParams
from timeturner.settings import ReportSettings

delta_components = re.compile(r"(?P<sign>[+-])?(?P<value>\d+)(?P<unit>[mhd])")
range_components = re.compile(r"(?P<value>\d+)?(?P<unit>[dwMyY]|day|week|month|year)s?")


class ComponentType(Enum):
    TIME = "time"
    DATE = "date"
    DELTA = "delta"
    DELTA_WITH_TIME = "delta_with_time"
    ALIAS = "alias"
    RANGE = "range"
    NUMBER = "number"
    UNKNOWN = "unknown"


class ListGroupBy(Enum):
    AUTO = "auto"
    DONT_GROUP = "dont_group"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class DateDict(TypedDict, total=False):
    year: int
    month: int
    day: int


class TimeDict(TypedDict, total=False):
    hour: int
    minute: int
    second: int


class DateTimeDict(TypedDict, total=False):
    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: int
    tzinfo: Any


def split_filter_tags(args: list[str]) -> tuple[list[str], list[str]]:
    tags = []
    filtered_args = []
    for arg in args:
        if arg.startswith("@"):
            tags.append(arg[1:])
        else:
            filtered_args.append(arg)
    return filtered_args, tags


def split_array(array: list[str], separator: str) -> tuple[list[str], list[str]]:
    try:
        index = array.index(separator)
    except ValueError:
        return array, []
    return array[:index], array[index + 1 :]


def get_component_type(component: str, *, include_list_args) -> ComponentType:
    if include_list_args:
        if component in ["today", "yesterday", "week", "month", "year"]:
            return ComponentType.ALIAS
        if range_components.match(component):
            return ComponentType.RANGE
    if component.startswith("-") or component.startswith("+"):
        if "@" in component:
            return ComponentType.DELTA_WITH_TIME
        return ComponentType.DELTA
    if ":" in component:
        return ComponentType.TIME
    if "-" in component:
        return ComponentType.DATE
    if component.isnumeric():
        return ComponentType.NUMBER
    return ComponentType.UNKNOWN


def parse_time(time: str, now: DateTime) -> DateTime:
    ret = TimeDict()
    match time.split(":"):
        case [hour, minute]:
            ret["hour"] = int(hour)
            ret["minute"] = int(minute)
        case [hour, minute, second]:
            ret["hour"] = int(hour)
            ret["minute"] = int(minute)
            ret["second"] = int(second)
        case _:
            raise ValueError(f"Invalid time: {time}")
    return now.set(**ret)


def parse_date(date: str, now: DateTime) -> DateTime:
    ret = DateDict()
    match date.split("-"):
        case [year, month, day]:
            ret["year"] = int(year)
            ret["month"] = int(month)
            ret["day"] = int(day)
        case [month, day]:
            ret["month"] = int(month)
            ret["day"] = int(day)
        case [day]:
            ret["day"] = int(day)
        case _:
            raise ValueError(f"Invalid date: {date}")
    return now.set(**ret)


def parse_delta(delta: str, now: DateTime) -> DateTime:
    ret = dict()
    matches = list(delta_components.finditer(delta))
    if not matches:
        raise ValueError(f"Invalid delta: {delta}")
    for match in matches:
        sign = match.group("sign")
        value = int(match.group("value"))
        unit = match.group("unit")
        if sign == "-":
            value = -value
        if unit == "d":
            ret["days"] = value
        elif unit == "h":
            ret["hours"] = value
        elif unit == "m":  # pragma: no branch
            ret["minutes"] = value

    return now + Duration(**ret)


def parse_delta_with_time(delta_with_time: str, now: DateTime) -> DateTime:
    DateTimeDict()
    delta, time = delta_with_time.split("@")
    now = parse_delta(delta, now)
    return parse_time(time, now)


def single_time_parse(
    components: list[str],
    *,
    now: DateTime | None = None,
    include_list_args: bool = False,
) -> DateTime:
    if now is None:
        now = pendulum.now()

    components_with_types = [
        (component, get_component_type(component, include_list_args=include_list_args))
        for component in components
    ]
    # print(components_with_types)
    match components_with_types:
        case [(time, ComponentType.TIME)]:
            now = parse_time(time, now)
        case [(date, ComponentType.DATE)] | [(date, ComponentType.NUMBER)]:
            now = parse_date(date, now)
        case [(delta, ComponentType.DELTA)]:
            now = parse_delta(delta, now)
        case [(delta, ComponentType.DELTA), (time, ComponentType.TIME)]:
            now = parse_delta(delta, now)
            now = parse_time(time, now)
        case [(delta_with_time, ComponentType.DELTA_WITH_TIME)]:
            now = parse_delta_with_time(delta_with_time, now)
        case [(date, ComponentType.DATE), (time, ComponentType.TIME)] | [
            (date, ComponentType.NUMBER),
            (time, ComponentType.TIME),
        ]:
            now = parse_date(date, now)
            now = parse_time(time, now)
        case []:
            pass
        case _:
            raise ValueError(f"Invalid components: {components}")
    return now.set(second=0, microsecond=0)


def parse_add_args(
    args: list[str],
    *,
    prefer_full_days: bool = False,
    holiday: bool = False,
    report_settings: ReportSettings,
) -> NewSegmentParams:
    args, tags = split_filter_tags(args)
    if holiday:
        if report_settings.holiday_tag not in tags:
            tags.append(report_settings.holiday_tag)
    for tag in tags:
        if tag not in report_settings.tag_settings:
            continue
        if report_settings.tag_settings[tag].full_day:
            prefer_full_days = True

    start, end = split_array(args, "-")
    start = single_time_parse(start)
    if end:
        end = single_time_parse(end, now=start)
    else:
        end = None
    if prefer_full_days:
        start = start.start_of("day")
        if not end:
            end = end_of_day(start)
        else:
            end = end_of_day(end)
    return NewSegmentParams(
        start=start,
        end=end,
        tags=tags,
    )


def parse_list_args(
    args: list[str],
    *,
    now: DateTime | None = None,
) -> tuple[DateTime, DateTime]:
    if now is None:
        now = pendulum.now()
    now = now.set(second=0, microsecond=0)
    start = now.start_of("day")
    end = end_of_day(now)
    if "-" in args:
        start, end = split_array(args, "-")
        start = single_time_parse(start, now=now)
        end = single_time_parse(end, now=start)

        if start.time() == now.time():
            start = start.start_of("day")
        if end.time() == now.time():
            end = end_of_day(end)

    elif len(args) == 0:
        pass
    elif len(args) == 1:
        arg = args[0]
        if arg in ["week", "month", "year"]:
            start = now.start_of(arg)
            end = end_of(now, arg)
        elif arg == "today":
            pass
        elif arg == "yesterday":
            start = start.subtract(days=1)
            end = end.subtract(days=1)
        elif _match := range_components.match(arg):
            match _match.groupdict():
                case {"value": value, "unit": "d" | "day" | "days"}:
                    start = start.subtract(days=int(value) - 1)
                case {"value": value, "unit": "w" | "week" | "weeks"}:
                    start = start.start_of("week").subtract(weeks=int(value) - 1)
                    end = end_of(now, "week")
                case {"value": value, "unit": "M" | "month" | "months"}:
                    start = start.start_of("month").subtract(months=int(value) - 1)
                    end = end_of(now, "month")
                case {  # pragma: no branch
                    "value": value,
                    "unit": "y" | "year" | "years",
                }:
                    start = start.start_of("year").subtract(years=int(value) - 1)
                    end = end_of(now, "year")

        else:
            start = single_time_parse(args, now=now).start_of("day")
    else:
        # we have 2 arguments, but no dash
        # we definitely define a specific time, so we don't change to
        # the start of the day, or the end of the day
        start = single_time_parse(args, now=now)

    return start, end
