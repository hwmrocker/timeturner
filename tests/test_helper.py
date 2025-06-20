from datetime import datetime

import pytest

from timeturner import helper

from .helpers import parse

ITER_OVER_DAYS_TESTS = [
    pytest.param(
        parse("1985-05-01 12:00"),
        parse("1985-05-01 14:00"),
        [parse("1985-05-01").date()],
        id="one day",
    ),
    pytest.param(
        parse("1985-05-01 14:00"),
        parse("1985-05-02 02:00"),
        [parse("1985-05-01").date(), parse("1985-05-02").date()],
        id="two days",
    ),
    pytest.param(
        parse("1985-05-01"),
        parse("1985-05-02"),
        [
            parse("1985-05-01").date(),
        ],
        id="one full day",
    ),
    pytest.param(
        parse("1985-05-01 14:00"),
        parse("1985-05-01 14:00"),
        [],
        id="one day, same start and end",
    ),
    pytest.param(
        parse("1985-05-01"),
        parse("1985-05-01"),
        [],
        id="one day, start and end at midnight",
    ),
]


@pytest.mark.parametrize("start, end, expected_days", ITER_OVER_DAYS_TESTS)
def test_iter_over_days(start, end, expected_days):
    list_of_days = list(helper.iter_over_days(start, end))
    assert list_of_days == expected_days


@pytest.mark.parametrize(
    "dt, arg, expected",
    [
        pytest.param(
            parse("1985-05-02 14:00:00"), "day", parse("1985-05-02"), id="day"
        ),
        pytest.param(
            parse("1985-05-02 14:00:00"), "month", parse("1985-05-01"), id="month"
        ),
        pytest.param(
            parse("1985-05-02 14:00:00"), "week", parse("1985-04-29"), id="week"
        ),
        pytest.param(
            parse("1985-05-02").date(), "week", parse("1985-04-29"), id="week from date"
        ),
    ],
)
def test_start_of(dt, arg, expected):
    result = helper.start_of(dt, arg)
    assert result == expected, f"Expected {expected=}, got {result=}"


@pytest.mark.parametrize(
    "dt, expected",
    [
        pytest.param(parse("1985-05-02 14:00:00"), parse("1985-05-03")),
        pytest.param(parse("1985-05-02").date(), parse("1985-05-03")),
    ],
)
def test_end_of_day(dt, expected):
    result = helper.end_of_day(dt)
    assert result == expected, f"Expected {expected=}, got {result=}"


@pytest.mark.parametrize(
    "dt, value, expected",
    [
        pytest.param(
            parse("1985-05-02"), {"days": 5}, parse("1985-04-27"), id="subtract days"
        ),
        pytest.param(
            parse("1985-05-02 12:00"),
            {"days": 1},
            parse("1985-05-01 12:00"),
            id="subtract 1 day with time",
        ),
        pytest.param(
            parse("1985-05-02 12:00"),
            {"hours": 2},
            parse("1985-05-02 10:00"),
            id="subtract hours",
        ),
        pytest.param(
            parse("1985-05-02 12:00"),
            {"minutes": 30},
            parse("1985-05-02 11:30"),
            id="subtract minutes",
        ),
        pytest.param(
            parse("1985-05-02 00:00"),
            {"days": 0},
            parse("1985-05-02 00:00"),
            id="subtract zero days",
        ),
        pytest.param(
            parse("1985-05-02 00:00"),
            {"days": -1},
            parse("1985-05-03 00:00"),
            id="add days with negative",
        ),
        pytest.param(
            parse("1985-05-02 12:00"),
            {"days": 1, "hours": 2},
            parse("1985-05-01 10:00"),
            id="subtract days and hours",
        ),
        # New test cases for weeks, months, years
        pytest.param(
            parse("1985-05-15"),
            {"weeks": 1},
            parse("1985-05-08"),
            id="subtract 1 week",
        ),
        pytest.param(
            parse("1985-05-15"),
            {"weeks": 4},
            parse("1985-04-17"),
            id="subtract 4 weeks",
        ),
        pytest.param(
            parse("1985-05-15"),
            {"months": 1},
            parse("1985-04-15"),
            id="subtract 1 month",
        ),
        pytest.param(
            parse("1985-05-15"),
            {"months": 6},
            parse("1984-11-15"),
            id="subtract 6 months",
        ),
        pytest.param(
            parse("1985-07-15"),
            {"months": -6},
            parse("1986-01-15"),
            id="subtract 6 months",
        ),
        pytest.param(
            parse("1985-05-15"),
            {"years": 1},
            parse("1984-05-15"),
            id="subtract 1 year",
        ),
        pytest.param(
            parse("1985-05-15"),
            {"years": 2, "months": 3, "days": 10},
            parse("1983-02-05"),
            id="subtract years, months, and days",
        ),
    ],
)
def test_dt_subtract(dt, value, expected):
    result = helper.dt_subtract(dt, **value)
    assert result == expected, f"Expected {expected=}, got {result=}"


@pytest.mark.parametrize(
    "dt, expected",
    [
        pytest.param(datetime.fromisoformat("1985-12-01 14:10:07+00:00"), 0),
        pytest.param(datetime.fromisoformat("1985-12-01 14:10:07+04:00"), -4),
        pytest.param(datetime.fromisoformat("1985-12-01 14:10:07-04:00"), 4),
    ],
)
def test_get_tz_offset(dt, expected):
    """
    Test that get_tz_offset returns the correct offset for a known datetime.
    """
    offset = helper.get_tz_offset(dt)
    assert offset == expected, f"Expected {expected=}, got {offset=}"


def test_get_tz_offset_error():
    dt = datetime.fromisoformat("1985-12-01 14:10:07")
    with pytest.raises(ValueError, match="must be timezone-aware"):
        helper.get_tz_offset(dt)
