import re

# from pendulum.tz.timezone import Timezone
from enum import Enum
from typing import Any, Literal, TypedDict, cast, overload

import pendulum
from pendulum.datetime import DateTime
from pendulum.duration import Duration

delta_components = re.compile(r"(?P<sign>[+-])?(?P<value>\d+)(?P<unit>[mhd])")


class ComponentType(Enum):
    TIME = "time"
    DATE = "date"
    DELTA = "delta"
    DELTA_WITH_TIME = "delta_with_time"


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


def split_array(array: list[str], separator: str) -> tuple[list[str], list[str]]:
    try:
        index = array.index(separator)
    except ValueError:
        return array, []
    return array[:index], array[index + 1 :]


def get_component_type(component: str) -> ComponentType:
    if component.startswith("-") or component.startswith("+"):
        if "@" in component:
            return ComponentType.DELTA_WITH_TIME
        return ComponentType.DELTA
    if ":" in component:
        return ComponentType.TIME
    if "-" in component:
        return ComponentType.DATE
    return ComponentType.DATE


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
    return now.set(**ret)


def parse_delta(delta: str, now: DateTime) -> DateTime:
    ret = dict()
    for match in delta_components.finditer(delta):
        sign = match.group("sign")
        value = int(match.group("value"))
        unit = match.group("unit")
        if sign == "-":
            value = -value
        if unit == "d":
            ret["days"] = value
        elif unit == "h":
            ret["hours"] = value
        elif unit == "m":
            ret["minutes"] = value

    return now + Duration(**ret)


def parse_delta_with_time(delta_with_time: str, now: DateTime) -> DateTime:
    ret = DateTimeDict()
    delta, time = delta_with_time.split("@")
    now = parse_delta(delta, now)
    return parse_time(time, now)


def single_time_parse(
    components: list[str],
    *,
    now: DateTime | None = None,
) -> DateTime:
    if now is None:
        now = pendulum.now()

    components_with_types = [
        (component, get_component_type(component)) for component in components
    ]
    # print(components_with_types)
    match components_with_types:
        case [(time, ComponentType.TIME)]:
            now = parse_time(time, now)
        case [(date, ComponentType.DATE)]:
            now = parse_date(date, now)
        case [(delta, ComponentType.DELTA)]:
            now = parse_delta(delta, now)
        case [(delta_with_time, ComponentType.DELTA_WITH_TIME)]:
            now = parse_delta_with_time(delta_with_time, now)
        case [(date, ComponentType.DATE), (time, ComponentType.TIME)]:
            now = parse_date(date, now)
            now = parse_time(time, now)
        case []:
            pass
        case _:
            raise ValueError(f"Invalid components: {components}")
    return now.set(second=0, microsecond=0)


@overload
def parse_args(
    args: list[str],
    *,
    single_time: Literal[True],
    prefer_full_days: bool = False,
) -> DateTime:
    ...


@overload
def parse_args(
    args: list[str],
    *,
    prefer_full_days: Literal[True],
) -> tuple[DateTime, DateTime]:
    ...


@overload
def parse_args(
    args: list[str],
    *,
    prefer_full_days: Literal[False],
) -> tuple[DateTime, DateTime | None]:
    ...


@overload
def parse_args(
    args: list[str],
) -> tuple[DateTime, DateTime | None]:
    ...


def parse_args(
    args: list[str],
    *,
    prefer_full_days: bool = False,
    single_time: bool = False,
) -> tuple[DateTime, DateTime | None] | DateTime:
    start, end = split_array(args, "-")
    start = single_time_parse(start)
    if end:
        end = single_time_parse(end, now=start)
    else:
        end = None
    if single_time:
        return start
    if prefer_full_days:
        start = start.start_of("day")
        if not end:
            end = start.end_of("day")
    return start, end
