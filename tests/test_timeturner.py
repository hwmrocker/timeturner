import pytest
from pendulum.time import Time

from tests.helpers import freeze_time_at_1985_25_05__15_34_12, parse
from timeturner import timeturner
from timeturner.db import DatabaseConnection, PensiveRow

pytestmark = pytest.mark.dependency(depends=["db_tests"], scope="session")


@freeze_time_at_1985_25_05__15_34_12
def test_add_segment(db: DatabaseConnection):
    assert timeturner.add(None, db=db).start == parse("1985-05-25 15:34:00")
    assert timeturner.add([], db=db).start == parse("1985-05-25 15:34:00")


GET_SUMMARY_TEST_CASES = [
    pytest.param(
        [],
        timeturner.DailySummary(),
        id="no segments",
    ),
    pytest.param(
        [
            PensiveRow(
                pk=1,
                start=parse("1985-05-25 00:00:00"),
                end=parse("1985-05-25 01:00:00"),
            ),
        ],
        timeturner.DailySummary(
            work_time=timeturner.Duration(hours=1),
            break_time=timeturner.Duration(),
            start=Time(0, 0),
            end=Time(1, 0),
        ),
        id="one short segment",
    ),
    pytest.param(
        [
            PensiveRow(
                pk=1,
                start=parse("1985-05-25 00:00:00"),
                end=parse("1985-05-25 01:00:00"),
            ),
            PensiveRow(
                pk=2,
                start=parse("1985-05-25 01:00:00"),
                end=parse("1985-05-25 02:00:00"),
            ),
        ],
        timeturner.DailySummary(
            work_time=timeturner.Duration(hours=2),
            break_time=timeturner.Duration(),
            start=Time(0, 0),
            end=Time(2, 0),
        ),
        id="two segments, no overlap",
    ),
    pytest.param(
        [
            PensiveRow(
                pk=1,
                start=parse("1985-05-25 00:00:00"),
                end=parse("1985-05-25 00:59:00"),
            ),
            PensiveRow(
                pk=2,
                start=parse("1985-05-25 01:00:00"),
                end=parse("1985-05-25 02:00:00"),
            ),
        ],
        timeturner.DailySummary(
            work_time=timeturner.Duration(hours=2),
            break_time=timeturner.Duration(),
            start=Time(0, 0),
            end=Time(2, 0),
        ),
        id="two segments, mini gap",
    ),
    pytest.param(
        [
            PensiveRow(
                pk=1,
                start=parse("1985-05-25 00:00:00"),
                end=parse("1985-05-25 00:59:00"),
            ),
            PensiveRow(
                pk=2,
                start=parse("1985-05-25 02:00:00"),
                end=parse("1985-05-25 03:00:00"),
            ),
        ],
        timeturner.DailySummary(
            work_time=timeturner.Duration(hours=1, minutes=59),
            break_time=timeturner.Duration(hours=1, minutes=1),
            start=Time(0, 0),
            end=Time(3, 0),
        ),
        id="two segments, with break",
    ),
    pytest.param(
        [
            PensiveRow(
                pk=1,
                start=parse("1985-05-25 00:00:00"),
                end=parse("1985-05-25 01:00:00"),
            ),
            PensiveRow(
                pk=2,
                start=parse("1985-05-25 02:00:00"),
                end=parse("1985-05-25 09:00:00"),
            ),
        ],
        timeturner.DailySummary(
            work_time=timeturner.Duration(hours=8, minutes=0),
            break_time=timeturner.Duration(hours=1, minutes=0),
            start=Time(0, 0),
            end=Time(9, 0),
        ),
        id="two segments, with long enough break",
    ),
    pytest.param(
        [
            PensiveRow(
                pk=1,
                start=parse("1985-05-25 00:00:00"),
                end=parse("1985-05-25 09:00:00"),
            ),
        ],
        timeturner.DailySummary(
            work_time=timeturner.Duration(hours=8, minutes=15),
            break_time=timeturner.Duration(minutes=45),
            start=Time(0, 0),
            end=Time(9, 0),
        ),
        id="one segments, without break",
    ),
    pytest.param(
        [
            PensiveRow(
                pk=1,
                start=parse("1985-05-25 00:00:00"),
                end=parse("1985-05-25 05:00:00"),
            ),
        ],
        timeturner.DailySummary(
            work_time=timeturner.Duration(hours=4, minutes=45),
            break_time=timeturner.Duration(minutes=15),
            start=Time(0, 0),
            end=Time(5, 0),
        ),
        id="one segments, without break",
    ),
    pytest.param(
        [
            PensiveRow(
                pk=1,
                start=parse("1985-05-25 00:00:00"),
                end=parse("1985-05-25 02:00:00"),
            ),
            PensiveRow(
                pk=1,
                start=parse("1985-05-25 02:30:00"),
                end=parse("1985-05-25 05:00:00"),
            ),
        ],
        timeturner.DailySummary(
            work_time=timeturner.Duration(hours=4, minutes=30),
            break_time=timeturner.Duration(minutes=30),
            start=Time(0, 0),
            end=Time(5, 0),
        ),
        id="two segments short, with break",
    ),
    pytest.param(
        [
            PensiveRow(
                pk=1,
                start=parse("1985-05-25 00:00:00"),
                end=parse("1985-05-25 02:00:00"),
                tags=["A", "B"],
            ),
            PensiveRow(
                pk=1,
                start=parse("1985-05-25 02:30:00"),
                end=parse("1985-05-25 05:00:00"),
                tags=["B", "C"],
            ),
        ],
        timeturner.DailySummary(
            work_time=timeturner.Duration(hours=4, minutes=30),
            break_time=timeturner.Duration(minutes=30),
            start=Time(0, 0),
            end=Time(5, 0),
            by_tag={
                "A": timeturner.Duration(hours=2),
                "B": timeturner.Duration(hours=4, minutes=30),
                "C": timeturner.Duration(hours=2, minutes=30),
            },
        ),
        id="segments with tags",
    ),
]


@pytest.mark.parametrize("segments, expected_summary", GET_SUMMARY_TEST_CASES)
def test_get_summary(segments, expected_summary):
    assert timeturner.get_daily_summary(segments) == expected_summary


ILLEGAL_SEGMENTS = [
    pytest.param(
        [
            PensiveRow(
                pk=1,
                start=parse("1985-05-25 00:00:00"),
            ),
            PensiveRow(
                pk=2,
                start=parse("1985-05-25 01:00:00"),
                end=parse("1985-05-25 02:00:00"),
            ),
        ],
        ValueError,
        id="two segments, first without end",
    ),
]


@pytest.mark.parametrize("segments, expected_error", ILLEGAL_SEGMENTS)
def test_get_summary_with_illegal_segments(segments, expected_error):
    with pytest.raises(expected_error):
        timeturner.get_daily_summary(segments)
