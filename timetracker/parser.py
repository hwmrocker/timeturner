import re
from enum import Enum
from typing import TypedDict

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


class DateTimeDict(DateDict, TimeDict):
    pass


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


def parse_time(time: str) -> TimeDict:
    ret = TimeDict()
    match time.split(":"):
        case [hour, minute]:
            ret["hour"] = int(hour)
            ret["minute"] = int(minute)
        case [hour, minute, second]:
            ret["hour"] = int(hour)
            ret["minute"] = int(minute)
            ret["second"] = int(second)
    return ret


def parse_date(date: str) -> DateDict:
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
    return ret


def parse_delta(delta: str, now: DateTime) -> DateTimeDict:
    ret = DateTimeDict()
    for match in delta_components.finditer(delta):
        sign = match.group("sign")
        value = int(match.group("value"))
        unit = match.group("unit")
        if sign == "-":
            value = -value
        if unit == "d":
            ret["day"] = now.day + value
        elif unit == "h":
            ret["hour"] = now.hour + value
        elif unit == "m":
            ret["minute"] = now.minute + value

    return ret


def parse_delta_with_time(delta_with_time: str, now: DateTime) -> DateTimeDict:
    ret = DateTimeDict()
    delta, time = delta_with_time.split("@")
    ret.update(**parse_delta(delta, now))
    ret.update(**parse_time(time))
    return ret


def single_time_parse(components: list[str]) -> DateTime:
    now = pendulum.now()

    default_date_time_components = dict(
        year=now.year,
        month=now.month,
        day=now.day,
        hour=now.hour,
        minute=now.minute,
        second=0,
        tzinfo=now.tzinfo,
    )

    components_with_types = [
        (component, get_component_type(component)) for component in components
    ]
    print(components_with_types)
    match components_with_types:
        case [(time, ComponentType.TIME)]:
            default_date_time_components.update(**parse_time(time))
        case [(date, ComponentType.DATE)]:
            default_date_time_components.update(**parse_date(date))
        case [(delta, ComponentType.DELTA)]:
            default_date_time_components.update(**parse_delta(delta, now))
        case [(delta_with_time, ComponentType.DELTA_WITH_TIME)]:
            default_date_time_components.update(
                **parse_delta_with_time(delta_with_time, now)
            )
        case [(date, ComponentType.DATE), (time, ComponentType.TIME)]:
            default_date_time_components.update(**parse_date(date))
            default_date_time_components.update(**parse_time(time))
        case []:
            pass
        case _:
            raise ValueError(f"Invalid components: {components}")
    return DateTime(**default_date_time_components)
