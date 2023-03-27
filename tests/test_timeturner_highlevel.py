import pytest
from pendulum.date import Date
from pendulum.duration import Duration

from tests.helpers import freeze_time_at_1985_25_05__15_34_12, parse
from timeturner import timeturner
from timeturner.db import DatabaseConnection

pytestmark = pytest.mark.dependency(depends=["db_tests"], scope="session")


@freeze_time_at_1985_25_05__15_34_12
def test_add_segment(db: DatabaseConnection):
    assert timeturner.add(None, db=db).start == parse("1985-05-25 15:34:00")
    assert timeturner.add([], db=db).start == parse("1985-05-25 15:34:00")


LIST_SEGMENTS_TESTS = [
    pytest.param(
        [],
        [
            Date(1985, 5, 25),
        ],
        id="no time args",
    ),
    pytest.param(
        None,
        [
            Date(1985, 5, 25),
        ],
        id="no time args",
    ),
    pytest.param(
        ["week"],
        [
            Date(1985, 5, 20),
            Date(1985, 5, 21),
            Date(1985, 5, 22),
            Date(1985, 5, 23),
            Date(1985, 5, 24),
            Date(1985, 5, 25),
            Date(1985, 5, 26),
        ],
        id="week",
    ),
]


@pytest.mark.parametrize("query, expected_days", LIST_SEGMENTS_TESTS)
@freeze_time_at_1985_25_05__15_34_12
def test_list_segments(db: DatabaseConnection, query, expected_days):
    timeturner.add(["1985-05-21", "9:00", "-", "+3h"], db=db)
    summaries = timeturner._list(query, db=db)
    assert [summary.day for summary in summaries] == expected_days
