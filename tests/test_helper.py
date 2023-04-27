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
