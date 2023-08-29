import pytest

from tests.helpers import freeze_time_at_1985_25_05__15_34_12, parse, test_now
from timeturner import models, parser
from timeturner.helper import end_of, end_of_day
from timeturner.settings import ReportSettings

# tz_offset = pendulum.now().offset_hours
default_report_settings = ReportSettings()


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
    pytest.param("12", parser.ComponentType.NUMBER, id="date day only"),
    pytest.param("04-12", parser.ComponentType.DATE, id="date with month and day"),
    pytest.param(
        "2022-04-12", parser.ComponentType.DATE, id="date with year, month and day"
    ),
]


@pytest.mark.parametrize(
    "include_list_args", [True, False]
)  # it should return the same result for those general cases
@pytest.mark.parametrize("component, expected", COMPONENT_TYPE_EXAMPLES)
def test_component_type(component, include_list_args, expected):
    assert (
        parser.get_component_type(component, include_list_args=include_list_args)
        == expected
    )


COMPONENT_TYPE_LIST_ARGS_EXAMPLES = [
    # pytest.param("now", parser.ComponentType.ALIAS, id="now"),
    pytest.param("today", parser.ComponentType.ALIAS, id="today"),
    pytest.param("yesterday", parser.ComponentType.ALIAS, id="yesterday"),
    pytest.param("week", parser.ComponentType.ALIAS, id="week"),
    pytest.param("month", parser.ComponentType.ALIAS, id="month"),
    pytest.param("year", parser.ComponentType.ALIAS, id="year"),
    pytest.param("1d", parser.ComponentType.RANGE, id="1d"),
    pytest.param("1day", parser.ComponentType.RANGE, id="1day"),
    pytest.param("1w", parser.ComponentType.RANGE, id="1w"),
    pytest.param("1week", parser.ComponentType.RANGE, id="1week"),
    pytest.param(
        "1M", parser.ComponentType.RANGE, id="1M"
    ),  # M can be only upper, lower case is too similar to minutes
    pytest.param("1month", parser.ComponentType.RANGE, id="1month"),
    pytest.param("1Y", parser.ComponentType.RANGE, id="1Y"),
    pytest.param(
        "1y", parser.ComponentType.RANGE, id="1y"
    ),  # y can be upper or lower case
    pytest.param("1year", parser.ComponentType.RANGE, id="1year"),
]


@pytest.mark.parametrize("component, expected", COMPONENT_TYPE_LIST_ARGS_EXAMPLES)
def test_component_type_list_args(component, expected):
    assert parser.get_component_type(component, include_list_args=True) == expected


@pytest.mark.parametrize("component, expected", COMPONENT_TYPE_LIST_ARGS_EXAMPLES)
def test_component_type_list_args_not_valid_for_add(component, expected):
    assert (
        parser.get_component_type(component, include_list_args=False)
        == parser.ComponentType.UNKNOWN
    )


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
@freeze_time_at_1985_25_05__15_34_12
def test_single_time_parse(components, expected):
    assert parser.single_time_parse(components) == expected


def test_single_time_parse_with_bad_input():
    with pytest.raises(ValueError):
        parser.single_time_parse(["zzz"])


PARSE_ADD_ARGS_EXAMPLES = [
    pytest.param(
        [],
        dict(),
        models.NewSegmentParams(
            start=parse("1985-05-25 15:34:00"),
            end=None,
            tags=[],
        ),
        id="no args",
    ),
    pytest.param(
        [],
        dict(prefer_full_days=True),
        models.NewSegmentParams(
            start=parse("1985-05-25"),
            end=parse("1985-05-26"),
            tags=[],
        ),
        id="no args, prefer full days",
    ),
    pytest.param(
        ["-2d", "-", "+1d"],
        dict(prefer_full_days=True),
        models.NewSegmentParams(
            start=parse("1985-05-23"),
            end=parse("1985-05-25"),
            tags=[],
        ),
        id="no args, prefer full days",
    ),
    pytest.param(
        ["23", "07:00", "-", "19:00"],
        dict(prefer_full_days=False),
        models.NewSegmentParams(
            start=parse("1985-05-23 07:00:00"),
            end=parse("1985-05-23 19:00:00"),
            tags=[],
        ),
        id="two days in the past",
    ),
    pytest.param(
        ["23", "07:00", "-", "+4h"],
        dict(prefer_full_days=False),
        models.NewSegmentParams(
            start=parse("1985-05-23 07:00:00"),
            end=parse("1985-05-23 11:00:00"),
            tags=[],
        ),
        id="two days in the past, with delta",
    ),
    pytest.param(
        [],
        dict(holiday=True),
        models.NewSegmentParams(
            start=parse("1985-05-25"),
            end=parse("1985-05-26"),
            tags=[default_report_settings.holiday_tag],
        ),
        id="no args, holiday",
    ),
    pytest.param(
        ["@holiday"],
        dict(holiday=True),
        models.NewSegmentParams(
            start=parse("1985-05-25"),
            end=parse("1985-05-26"),
            tags=[default_report_settings.holiday_tag],
        ),
        id="@holiday, with holiday=True",
    ),
    pytest.param(
        ["@holiday"],
        dict(),
        models.NewSegmentParams(
            start=parse("1985-05-25"),
            end=parse("1985-05-26"),
            tags=[default_report_settings.holiday_tag],
        ),
        id="no args, @holiday",
    ),
    pytest.param(
        ["1985-05-01", "@holiday"],
        dict(),
        models.NewSegmentParams(
            start=parse("1985-05-01"),
            end=parse("1985-05-02"),
            tags=[default_report_settings.holiday_tag],
        ),
        id="past date, @holiday",
    ),
]


@pytest.mark.parametrize("args, kwargs, expected", PARSE_ADD_ARGS_EXAMPLES)
@freeze_time_at_1985_25_05__15_34_12
def test_parse_add_args(args, kwargs, expected):
    add_kwargs = dict(
        report_settings=default_report_settings,
    )
    add_kwargs.update(kwargs)
    observed = parser.parse_add_args(
        args,
        **add_kwargs,  # type: ignore
    )
    assert observed == expected


PARSE_LIST_ARGS_EXAMPLES = [
    pytest.param(
        [],
        dict(),
        (test_now.start_of("day"), end_of_day(test_now)),
        id="no args",
    ),
    pytest.param(
        [],
        dict(
            now=test_now.add(days=1),
        ),
        (test_now.add(days=1).start_of("day"), end_of_day(test_now.add(days=1))),
        id="no args, passing now",
    ),
    pytest.param(
        ["2d"],  # checking yesterday and today
        dict(),
        (test_now.subtract(days=1).start_of("day"), end_of_day(test_now)),
        id="2d",
    ),
    pytest.param(
        ["2days"],  # checking yesterday and today
        dict(),
        (test_now.subtract(days=1).start_of("day"), end_of_day(test_now)),
        id="2days",
    ),
    pytest.param(
        ["week"],  # checking current week
        dict(),
        (test_now.start_of("week"), end_of(test_now, "week")),
        id="week",
    ),
    pytest.param(
        ["month"],  # checking current month
        dict(),
        (test_now.start_of("month"), end_of(test_now, "month")),
        id="month",
    ),
    pytest.param(
        ["year"],  # checking current year
        dict(),
        (test_now.start_of("year"), end_of(test_now, "year")),
        id="year",
    ),
    pytest.param(
        ["today"],  # checking today
        dict(),
        (test_now.start_of("day"), end_of_day(test_now)),
        id="today",
    ),
    pytest.param(
        ["yesterday"],  # checking yesterday
        dict(),
        (
            test_now.subtract(days=1).start_of("day"),
            end_of_day(test_now.subtract(days=1)),
        ),
        id="yesterday",
    ),
    pytest.param(
        ["4w"],  # checking last 4 weeks
        dict(),
        (test_now.subtract(weeks=3).start_of("week"), end_of(test_now, "week")),
        id="4w",
    ),
    pytest.param(
        ["4week"],  # checking last 4 weeks
        dict(),
        (test_now.subtract(weeks=3).start_of("week"), end_of(test_now, "week")),
        id="4week",
    ),
    pytest.param(
        ["4weeks"],  # checking last 4 weeks
        dict(),
        (test_now.subtract(weeks=3).start_of("week"), end_of(test_now, "week")),
        id="4weeks",
    ),
    pytest.param(
        ["4M"],  # checking last 4 months
        dict(),
        (test_now.subtract(months=3).start_of("month"), end_of(test_now, "month")),
        id="4M",
    ),
    pytest.param(
        ["1y"],  # checking current year
        dict(),
        (test_now.start_of("year"), end_of(test_now, "year")),
        id="1y",
    ),
    pytest.param(
        ["2years"],  # checking last and current year
        dict(),
        (test_now.subtract(years=1).start_of("year"), end_of(test_now, "year")),
        id="2years",
    ),
    pytest.param(
        ["14"],  # checking since the 14th of the current month
        dict(),
        (
            test_now.set(day=14).start_of("day"),
            end_of_day(test_now),
        ),
        id="14",
    ),
    pytest.param(
        ["14", "12:00"],  # checking since the 14th of the current month
        dict(),
        (
            test_now.set(day=14, hour=12, minute=0, second=0),
            end_of_day(test_now),
        ),
        id="14 12:00",
    ),
    pytest.param(
        ["-17d", "-", "+4d"],  # checking since the 14th of the current month
        dict(),
        (
            test_now.set(day=8).start_of("day"),
            end_of_day(test_now.set(day=12)),
        ),
        id="-17d - +4d",
    ),
    pytest.param(
        [
            "-17d",
            "7:00",
            "-",
            "+4d",
            "18:00",
        ],  # checking since the 14th of the current month
        dict(),
        (
            test_now.start_of("day").set(day=8, hour=7),
            test_now.start_of("day").set(day=12, hour=18),
        ),
        id="-17d 7:00 - +4d 18:00",
    ),
]


@pytest.mark.parametrize("args, config, expected", PARSE_LIST_ARGS_EXAMPLES)
@freeze_time_at_1985_25_05__15_34_12
def test_parse_list_args(args, config, expected):
    observed = parser.parse_list_args(args, **config)
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
