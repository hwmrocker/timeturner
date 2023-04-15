import pytest
from pendulum.date import Date

from tests.helpers import freeze_time_at_1985_25_05__15_34_12, parse
from timeturner import timeturner
from timeturner.db import DatabaseConnection
from timeturner.settings import ReportSettings

pytestmark = pytest.mark.dependency(depends=["db_tests"], scope="session")

ADD_TEST_CASES = [
    pytest.param(
        [[]],
        [(parse("1985-05-25 15:34:00"), None)],
        id="no time args",
    ),
    pytest.param(
        [None],
        [(parse("1985-05-25 15:34:00"), None)],
        id="None time args",
    ),
    pytest.param(
        [["9:00", "-", "+3h"]],
        [(parse("1985-05-25 09:00:00"), parse("1985-05-25 12:00:00"))],
        id="start with end",
    ),
    pytest.param(
        [["9:00", "-", "+3h"], []],
        [
            (parse("1985-05-25 09:00:00"), parse("1985-05-25 12:00:00")),
            (parse("1985-05-25 15:34:00"), None),
        ],
        id="2nd segment",
    ),
    pytest.param(
        [["9:00"], []],
        [
            (parse("1985-05-25 09:00:00"), parse("1985-05-25 15:34:00")),
            (parse("1985-05-25 15:34:00"), None),
        ],
        id="auto end previous segment",
    ),
    pytest.param(
        [["9:00", "-", "+3h"], ["11:00"]],
        [
            (parse("1985-05-25 09:00:00"), parse("1985-05-25 11:00:00")),
            (parse("1985-05-25 11:00:00"), None),
        ],
        id="move previous end",
    ),
    pytest.param(
        [["9:00"], ["8:00"]],
        [
            (parse("1985-05-25 08:00:00"), parse("1985-05-25 09:00:00")),
            (parse("1985-05-25 09:00:00"), None),
        ],
        id="auto end segment that happened before",
    ),
    pytest.param(
        [["9:00"], ["8:00", "-", "9:30"]],
        [
            (parse("1985-05-25 09:30:00"), None),
            (parse("1985-05-25 08:00:00"), parse("1985-05-25 09:30:00")),
        ],
        id="move start from next segment",
    ),
    pytest.param(
        [["9:00", "-", "10:00"], ["8:00", "-", "9:30"]],
        [
            (parse("1985-05-25 09:30:00"), parse("1985-05-25 10:00:00")),
            (parse("1985-05-25 08:00:00"), parse("1985-05-25 09:30:00")),
        ],
        id="move start from next segment",
    ),
    pytest.param(
        [["9:00", "-", "9:15"], ["8:00", "-", "9:30"]],
        [
            (parse("1985-05-25 08:00:00"), parse("1985-05-25 09:30:00")),
        ],
        id="new segment fully overlaps previous",
    ),
    pytest.param(
        [["9:00", "-", "10:00"], ["8:00", "-", "8:30"]],
        [
            (parse("1985-05-25 09:00:00"), parse("1985-05-25 10:00:00")),
            (parse("1985-05-25 08:00:00"), parse("1985-05-25 08:30:00")),
        ],
        id="add segment before",
    ),
    pytest.param(
        [["9:00", "-", "10:00"], ["9:15", "-", "9:30"]],
        [
            (parse("1985-05-25 09:00:00"), parse("1985-05-25 09:15:00")),
            (parse("1985-05-25 09:15:00"), parse("1985-05-25 09:30:00")),
            (parse("1985-05-25 09:30:00"), parse("1985-05-25 10:00:00")),
        ],
        id="new segment in middle of previous",
    ),
    pytest.param(
        [["9:00", "-", "10:00"], ["10:00", "-", "11:00"], ["9:30", "-", "10:30"]],
        [
            (parse("1985-05-25 09:00:00"), parse("1985-05-25 09:30:00")),
            (parse("1985-05-25 09:30:00"), parse("1985-05-25 10:30:00")),
            (parse("1985-05-25 10:30:00"), parse("1985-05-25 11:00:00")),
        ],
        id="new segment in middle of two",
    ),
    pytest.param(
        [
            ["9:00", "-", "09:55"],
            ["9:55", "-", "10:05"],
            ["10:05", "-", "11:00"],
            ["9:30", "-", "10:30"],
        ],
        [
            (parse("1985-05-25 09:00:00"), parse("1985-05-25 09:30:00")),
            (parse("1985-05-25 09:30:00"), parse("1985-05-25 10:30:00")),
            (parse("1985-05-25 10:30:00"), parse("1985-05-25 11:00:00")),
        ],
        id="new segment in middle of two, plus overwrite",
    ),
    pytest.param(
        [
            ["2000-01-01", "0:00", "-", "2000-01-01", "23:59:59"],
            ["9:00"],
        ],
        [
            (parse("1985-05-25 09:00:00"), None),
            (parse("2000-01-01 00:00:00"), parse("2000-01-01 23:59:00")),
        ],
        id="future segment, don't end new segment",
    ),
    pytest.param(
        [
            ["9:00"],
            ["1985-05-01", "@holiday"],
        ],
        [
            (parse("1985-05-01 00:00:00"), parse("1985-05-01").end_of("day")),
            (parse("1985-05-25 09:00:00"), None),
        ],
        id="past day, @holiday",
    ),
    pytest.param(
        [
            ["9:00", "@random_tag"],
        ],
        [
            (parse("1985-05-25 09:00:00"), None),
        ],
        id="add segment with tag",
    ),
]


@pytest.mark.parametrize("args_list, expected_start_end_times", ADD_TEST_CASES)
@freeze_time_at_1985_25_05__15_34_12
def test_add_segment(db: DatabaseConnection, args_list, expected_start_end_times):
    for args in args_list:
        timeturner.add(args, db=db, report_settings=ReportSettings())
    all_segments = db.get_all_segments()
    start_and_end_times = [(segment.start, segment.end) for segment in all_segments]
    print(start_and_end_times)
    assert sorted(start_and_end_times) == sorted(expected_start_end_times)


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
    report_settings = ReportSettings()
    timeturner.add(
        ["1985-05-21", "9:00", "-", "+3h"],
        report_settings=report_settings,
        db=db,
    )
    summaries = timeturner.list_(
        query,
        report_settings=report_settings,
        db=db,
    )
    assert [summary.day for summary in summaries] == expected_days
