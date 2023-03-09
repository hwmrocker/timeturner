from typing import cast

import pytest
from freezegun import freeze_time
from pendulum.datetime import DateTime
from pendulum.parser import parse as _parse

from timeturner import parser

# tz_offset = pendulum.now().offset_hours


def parse(date_string) -> DateTime:
    """Parse a date string using pendulum but adding the local timezone."""
    return cast(DateTime, _parse(date_string, tz="local"))


COMPONENT_TYPE_EXAMPLES = [
    pytest.param("9:00", parser.ComponentType.TIME, id="time"),
    pytest.param("24:00", parser.ComponentType.TIME, id="24h time"),
    pytest.param("09:00", parser.ComponentType.TIME, id="time with leading zero"),
    pytest.param("9:00:00", parser.ComponentType.TIME, id="time with seconds"),
    pytest.param("-1m", parser.ComponentType.DELTA, id="-delta minutes"),
    pytest.param("+1m", parser.ComponentType.DELTA, id="+delta minutes"),
    pytest.param("-1h", parser.ComponentType.DELTA, id="-delta hours"),
    pytest.param("+1h", parser.ComponentType.DELTA, id="+delta hours"),
    pytest.param("-1d", parser.ComponentType.DELTA, id="-delta days"),
    pytest.param("+1d", parser.ComponentType.DELTA, id="+delta days"),
    pytest.param("-1h15m", parser.ComponentType.DELTA, id="-delta hours and minutes"),
    pytest.param(
        "-1d@9:00", parser.ComponentType.DELTA_WITH_TIME, id="-delta days with time"
    ),
    pytest.param("12", parser.ComponentType.DATE, id="date day only"),
    pytest.param("04-12", parser.ComponentType.DATE, id="date with month and day"),
    pytest.param(
        "2022-04-12", parser.ComponentType.DATE, id="date with year, month and day"
    ),
]


@pytest.mark.parametrize("component, expected", COMPONENT_TYPE_EXAMPLES)
def test_component_type(component, expected):
    assert parser.get_component_type(component) == expected


"""
| Example         | Description                               |
| --------------- | ----------------------------------------- |
|                 | now                                       |
| 9:00            | 9:00 today                                |
| -1m             | 1 minute ago                              |
| -1h             | 1 hour ago                                |
| -1d             | 1 day ago, you will be asked for the time |
| -1d@9:00        | 1 day ago 9:00                            |
| +1m             | 1 minute from now                         |
| +1h             | 1 hour from now                           |
| 12 7:00         | 7:00 on the 12th of the current month     |
| 02-28 9:00      | 9:00 on February 28 of the current year   |
| 2022-02-28 9:00 | 9:00 on February 28, 2022                 |
"""

SINGLE_TIME_EXAMPLES = [
    pytest.param([], parse("1985-05-25 15:34:00"), id="now"),
    pytest.param(["9:00"], parse("1985-05-25 09:00:00"), id="9:00"),
    pytest.param(
        ["9:00:15"], parse("1985-05-25 09:00:00"), id="9:00:15"
    ),  # seconds are ignored
    pytest.param(["-1m"], parse("1985-05-25 15:33:00"), id="-1m"),
    pytest.param(["-35m"], parse("1985-05-25 14:59:00"), id="-m underflow"),
    pytest.param(["-1h"], parse("1985-05-25 14:34:00"), id="-1h"),
    pytest.param(["-1d"], parse("1985-05-24 15:34:00"), id="-1d"),
    pytest.param(["-1d@9:00"], parse("1985-05-24 09:00:00"), id="-1d@9:00"),
    pytest.param(["-1d", "9:00"], parse("1985-05-24 09:00:00"), id="-1d@9:00"),
    pytest.param(["+27m"], parse("1985-05-25 16:01:00"), id="+m overflow"),
    pytest.param(["+120m"], parse("1985-05-25 17:34:00"), id="+120m"),
    pytest.param(["+1h"], parse("1985-05-25 16:34:00"), id="+1h"),
    pytest.param(["12"], parse("1985-05-12 15:34:00"), id="12"),
    pytest.param(["12", "7:00"], parse("1985-05-12 07:00:00"), id="12 7:00"),
    pytest.param(["02-28", "9:00"], parse("1985-02-28 09:00:00"), id="02-28 9:00"),
    pytest.param(
        ["2022-02-28", "9:00"], parse("2022-02-28 09:00:00"), id="2022-02-28 9:00"
    ),
]


@pytest.mark.parametrize("components, expected", SINGLE_TIME_EXAMPLES)
@freeze_time(
    "1985-05-25 15:34:12",
    tz_offset=-int(parse("1985-05-25 15:34:12").offset_hours),
)
def test_single_time_parse(components, expected):
    assert parser.single_time_parse(components) == expected


def test_single_time_parse_with_bad_input():
    with pytest.raises(ValueError):
        parser.single_time_parse(["zzz"])


PARSE_ARGS_EXAMPLES = [
    pytest.param([], False, (parse("1985-05-25 15:34:00"), None), id="no args"),
    pytest.param(
        [],
        True,
        (parse("1985-05-25 00:00:00"), parse("1985-05-25 00:00:00").end_of("day")),
        id="no args, prefer full days",
    ),
    pytest.param(
        ["-2d", "-", "+1d"],
        True,
        (parse("1985-05-23 00:00:00"), parse("1985-05-24 00:00:00").end_of("day")),
        id="no args, prefer full days",
    ),
    pytest.param(
        ["23", "07:00", "-", "19:00"],
        False,
        (parse("1985-05-23 07:00:00"), parse("1985-05-23 19:00:00")),
        id="two days in the past",
    ),
    pytest.param(
        ["23", "07:00", "-", "+4h"],
        False,
        (parse("1985-05-23 07:00:00"), parse("1985-05-23 11:00:00")),
        id="two days in the past, with delta",
    ),
]


@pytest.mark.parametrize("single_time", [True, False])
@pytest.mark.parametrize("args, prefer_full_days, expected", PARSE_ARGS_EXAMPLES)
@freeze_time(
    "1985-05-25 15:34:12",
    tz_offset=-int(parse("1985-05-25 15:34:12").offset_hours),
)
def test_parse_args(args, single_time, prefer_full_days, expected):
    if single_time:
        expected = expected[0]
    observed = parser.parse_args(
        args,
        single_time=single_time,
        prefer_full_days=prefer_full_days,
    )
    assert observed == expected


def test_parse_delta_with_bad_input():
    with pytest.raises(ValueError):
        parser.parse_delta("-4s", parse("1985-05-25 15:34:00"))


@pytest.mark.parametrize("badinput", ["zzzz-02-29", "", "1-2-3-4"])
def test_parse_date_with_bad_input(badinput):
    with pytest.raises(ValueError):
        parser.parse_date(badinput, parse("1985-05-25 15:34:00"))


def test_parse_time_with_bad_input():
    with pytest.raises(ValueError):
        parser.parse_time("14", parse("1985-05-25 15:34:00"))
