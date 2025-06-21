from datetime import date, datetime, timedelta
from functools import partial
from itertools import zip_longest

import pytest

from tests.helpers import freeze_time_at, freeze_time_at_1985_05_25__15_34_12, parse
from timeturner import timeturner
from timeturner.db import DatabaseConnection
from timeturner.settings import ReportSettings, TagSettings

# pytestmark = pytest.mark.dependency(
#     depends=["db_tests", "timetracker_unit"], scope="session"
# )

default_report_settings = ReportSettings()
default_report_settings.tag_settings["prio1"] = TagSettings(
    name="prio1",
    priority=1,
)


def tt_test_case(
    input_args: list[list[str] | tuple[str, list[str]]],
    expected: list[tuple[datetime, datetime | None, list[str]]],
    id: str,
):
    """
    Helper to create a pytest parameterized test case for timeturner high-level segment logic.

    Args:
        input_args: A list of argument lists or tuples. If a tuple, the first element is the function name (e.g., "add" or "end"),
                    and the second is the argument list. If a list, "add" is assumed as the function.
        expected: A list of tuples (start, end, tags) representing the expected segments after all operations.
        id: The pytest case id.

    Returns:
        A pytest.param object for use in parameterized tests, where each input is a partial function ready to be called.

    Examples:
        # Example 1: Add a segment with no arguments (defaults to now)
        tt_test_case(
            [[]],
            [(parse("1985-05-25 15:34:00"), None, [])],
            id="no time args"
        )

        # Example 2: Add a segment and then end it
        tt_test_case(
            [["9:00"], ("end", ["12:00"])],
            [(parse("1985-05-25 09:00:00"), parse("1985-05-25 12:00:00"), [])],
            id="add and end segment"
        )
    """
    prepared_partials = []
    for maybe_args in input_args:
        if isinstance(maybe_args, tuple):
            func_name, args = maybe_args
        else:
            func_name = "add"
            args = maybe_args
        func = getattr(timeturner, func_name)
        prepared_partials.append(partial(func, args))
    return pytest.param(
        prepared_partials,
        expected,
        id=id,
    )


ADD_TEST_CASES = [
    tt_test_case(
        [[]],
        [(parse("1985-05-25 15:34:00"), None, [])],
        id="no time args",
    ),
    tt_test_case(
        [None],  # type: ignore
        [(parse("1985-05-25 15:34:00"), None, [])],
        id="None time args",
    ),
    tt_test_case(
        [["9:00", "-", "+3h"]],
        [(parse("1985-05-25 09:00:00"), parse("1985-05-25 12:00:00"), [])],
        id="start with end",
    ),
    tt_test_case(
        [["9:00", "-", "+3h"], []],
        [
            (parse("1985-05-25 09:00:00"), parse("1985-05-25 12:00:00"), []),
            (parse("1985-05-25 15:34:00"), None, []),
        ],
        id="2nd segment",
    ),
    tt_test_case(
        [["9:00"], []],
        [
            (parse("1985-05-25 09:00:00"), parse("1985-05-25 15:34:00"), []),
            (parse("1985-05-25 15:34:00"), None, []),
        ],
        id="auto end previous segment",
    ),
    tt_test_case(
        [["9:00", "-", "+3h"], ["11:00"]],
        [
            (parse("1985-05-25 09:00:00"), parse("1985-05-25 11:00:00"), []),
            (parse("1985-05-25 11:00:00"), None, []),
        ],
        id="move previous end",
    ),
    tt_test_case(
        [["9:00"], ["8:00"]],
        [
            (parse("1985-05-25 08:00:00"), parse("1985-05-25 09:00:00"), []),
            (parse("1985-05-25 09:00:00"), None, []),
        ],
        id="auto end segment that happened before",
    ),
    tt_test_case(
        [["9:00"], ["8:00", "-", "9:30"]],
        [
            (parse("1985-05-25 09:30:00"), None, []),
            (parse("1985-05-25 08:00:00"), parse("1985-05-25 09:30:00"), []),
        ],
        id="move start from next segment",
    ),
    tt_test_case(
        [["9:00", "-", "10:00"], ["8:00", "-", "9:30"]],
        [
            (parse("1985-05-25 09:30:00"), parse("1985-05-25 10:00:00"), []),
            (parse("1985-05-25 08:00:00"), parse("1985-05-25 09:30:00"), []),
        ],
        id="move start from next segment",
    ),
    tt_test_case(
        [["9:00", "-", "9:15"], ["8:00", "-", "9:30"]],
        [
            (parse("1985-05-25 08:00:00"), parse("1985-05-25 09:30:00"), []),
        ],
        id="new segment fully overlaps previous",
    ),
    tt_test_case(
        [["9:00", "-", "10:00"], ["8:00", "-", "8:30"]],
        [
            (parse("1985-05-25 09:00:00"), parse("1985-05-25 10:00:00"), []),
            (parse("1985-05-25 08:00:00"), parse("1985-05-25 08:30:00"), []),
        ],
        id="add segment before",
    ),
    tt_test_case(
        [["9:00", "-", "10:00"], ["9:15", "-", "9:30"]],
        [
            (parse("1985-05-25 09:00:00"), parse("1985-05-25 09:15:00"), []),
            (parse("1985-05-25 09:15:00"), parse("1985-05-25 09:30:00"), []),
            (parse("1985-05-25 09:30:00"), parse("1985-05-25 10:00:00"), []),
        ],
        id="new segment in middle of previous",
    ),
    tt_test_case(
        [["9:00", "-", "10:00"], ["10:00", "-", "11:00"], ["9:30", "-", "10:30"]],
        [
            (parse("1985-05-25 09:00:00"), parse("1985-05-25 09:30:00"), []),
            (parse("1985-05-25 09:30:00"), parse("1985-05-25 10:30:00"), []),
            (parse("1985-05-25 10:30:00"), parse("1985-05-25 11:00:00"), []),
        ],
        id="new segment in middle of two",
    ),
    tt_test_case(
        [
            ["9:00", "-", "09:55"],
            ["9:55", "-", "10:05"],
            ["10:05", "-", "11:00"],
            ["9:30", "-", "10:30"],
        ],
        [
            (parse("1985-05-25 09:00:00"), parse("1985-05-25 09:30:00"), []),
            (parse("1985-05-25 09:30:00"), parse("1985-05-25 10:30:00"), []),
            (parse("1985-05-25 10:30:00"), parse("1985-05-25 11:00:00"), []),
        ],
        id="new segment in middle of two, plus overwrite",
    ),
    tt_test_case(
        [
            ["2000-01-01", "0:00", "-", "2000-01-01", "23:59:59"],
            ["9:00"],
        ],
        [
            (parse("1985-05-25 09:00:00"), None, []),
            (parse("2000-01-01 00:00:00"), parse("2000-01-01 23:59:00"), []),
        ],
        id="future segment, don't end new segment",
    ),
    tt_test_case(
        [
            ["9:00"],
            ["1985-05-01", "@holiday"],
        ],
        [
            (
                parse("1985-05-01"),
                parse("1985-05-02"),
                ["holiday"],
            ),
            (parse("1985-05-25 09:00:00"), None, []),
        ],
        id="past day, @holiday",
    ),
    tt_test_case(
        [
            ["9:00", "@random_tag"],
        ],
        [
            (parse("1985-05-25 09:00:00"), None, ["random_tag"]),
        ],
        id="add segment with tag",
    ),
    tt_test_case(
        [
            ["9:00", "@travel"],
        ],
        [
            (parse("1985-05-25 09:00:00"), None, ["travel"]),
        ],
        id="add segment with defined non full day tag",
    ),
    tt_test_case(
        [
            ["05-01", "@vacation"],
        ],
        [
            (
                parse("1985-05-01"),
                parse("1985-05-02"),
                ["vacation"],
            ),
        ],
        id="vacation is full day",
    ),
    tt_test_case(
        [
            ["05-01", "@vacation"],
            ["05-01", "@holiday"],
        ],
        [
            (
                parse("1985-05-01"),
                parse("1985-05-02"),
                ["holiday"],
            ),
        ],
        id="holiday is overiding vacation",
    ),
    tt_test_case(
        [
            ["05-01", "@holiday"],
            ["05-01", "@vacation"],
        ],
        [
            (
                parse("1985-05-01"),
                parse("1985-05-02"),
                ["holiday"],
            ),
        ],
        id="vacation can't override holiday",
    ),
    tt_test_case(
        [
            ["04-29", "-", "05-02", "@vacation"],
            ["05-01", "-", "05-05", "@holiday"],
        ],
        [
            (parse("1985-04-29"), parse("1985-05-01"), ["vacation"]),
            (parse("1985-05-01"), parse("1985-05-06"), ["holiday"]),
        ],
        id="move start from next segment, different prios, lower prio first",
    ),
    tt_test_case(
        [
            ["05-01", "-", "05-05", "@holiday"],
            ["04-29", "-", "05-02", "@vacation"],
        ],
        [
            (parse("1985-04-29"), parse("1985-05-01"), ["vacation"]),
            (parse("1985-05-01"), parse("1985-05-06"), ["holiday"]),
        ],
        id="move start from next segment, different prios, higer prio first",
    ),
    tt_test_case(
        [
            ["04-30", "-", "05-03", "@vacation"],
            ["05-01", "@holiday"],
        ],
        [
            (parse("1985-04-30"), parse("1985-05-01"), ["vacation"]),
            (parse("1985-05-01"), parse("1985-05-02"), ["holiday"]),
            (parse("1985-05-02"), parse("1985-05-04"), ["vacation"]),
        ],
        id="holiday in the middle of vacation, will split it",
    ),
    tt_test_case(
        [
            ["05-01", "@holiday"],
            ["04-29", "-", "05-03", "@vacation"],
        ],
        [
            (parse("1985-04-29"), parse("1985-05-01"), ["vacation"]),
            (parse("1985-05-01"), parse("1985-05-02"), ["holiday"]),
            (parse("1985-05-02"), parse("1985-05-04"), ["vacation"]),
        ],
        id="vacation around holiday, will be split",
    ),
    tt_test_case(
        [["12-24", "-", "12-26", "@holiday"], ["12-25", "-", "12-31", "@vacation"]],
        [
            (parse("1985-12-24"), parse("1985-12-27"), ["holiday"]),
            (parse("1985-12-27"), parse("1985-12-28"), ["vacation"]),
            (parse("1985-12-30"), parse("1986-01-01"), ["vacation"]),
        ],
        id="vacation starts during holiday, including weekend",
    ),
    tt_test_case(
        [
            ["12-24", "-", "12-26", "@holiday"],
            ["12-31", "-", "1986-01-01", "@holiday"],
            ["12-25", "-", "1986-01-06", "@vacation"],
        ],
        [
            (parse("1985-12-24"), parse("1985-12-27"), ["holiday"]),
            (parse("1985-12-27"), parse("1985-12-28"), ["vacation"]),
            (parse("1985-12-30"), parse("1985-12-31"), ["vacation"]),
            (parse("1985-12-31"), parse("1986-01-02"), ["holiday"]),
            (parse("1986-01-02"), parse("1986-01-04"), ["vacation"]),
            (parse("1986-01-06"), parse("1986-01-07"), ["vacation"]),
        ],
        id="vacation with multiple holidays",
    ),
    tt_test_case(
        [
            ["12-24", "-", "12-26", "@holiday"],
            ["12-31", "-", "1986-01-01", "@holiday"],
            ["12-20", "-", "1986-01-06", "@vacation"],
        ],
        [
            (parse("1985-12-20"), parse("1985-12-21"), ["vacation"]),
            # 21 & 22 Saturday and Sunday
            (parse("1985-12-23"), parse("1985-12-24"), ["vacation"]),
            (parse("1985-12-24"), parse("1985-12-27"), ["holiday"]),
            (parse("1985-12-27"), parse("1985-12-28"), ["vacation"]),
            # 28 & 29 Saturday and Sunday
            (parse("1985-12-30"), parse("1985-12-31"), ["vacation"]),
            (parse("1985-12-31"), parse("1986-01-02"), ["holiday"]),
            (parse("1986-01-02"), parse("1986-01-04"), ["vacation"]),
            # 4 & 5 Saturday and Sunday
            (parse("1986-01-06"), parse("1986-01-07"), ["vacation"]),
        ],
        id="another vacation with multiple holidays",
    ),
    tt_test_case(
        [
            ["08-01", "-", "08-05", "@holiday"],  # assume company holiday
            [
                "08-02",
                "-",
                "08-04",
                "@vacation",
            ],
        ],
        [
            (parse("1985-08-01"), parse("1985-08-06"), ["holiday"]),
        ],
        id="vacation is inside company holiday",
    ),
    tt_test_case(
        [
            ("add", ["08-01", "-", "08-08", "@vacation"]),
        ],
        [
            (parse("1985-08-01"), parse("1985-08-03"), ["vacation"]),
            (parse("1985-08-05"), parse("1985-08-09"), ["vacation"]),
        ],
        id="long vacation is split by weekends",
    ),
    tt_test_case(
        [
            ["08-01", "@vacation"],  # one vacation day in the future
            ["07:00"],  # start of work day
            ("end", ["12:00"]),  # end of work day
        ],
        [
            (parse("1985-05-25 07:00"), parse("1985-05-25 12:00:00"), []),
            (parse("1985-08-01"), parse("1985-08-02"), ["vacation"]),
        ],
        id="vacation in the future should not affect end function",
    ),
    tt_test_case(
        [["9:00", "-", "+3h"], ["@sick"]],
        [
            (parse("1985-05-25 09:00:00"), parse("1985-05-25 12:00:00"), []),
            (parse("1985-05-25 00:00:00"), parse("1985-05-26 00:00:00"), ["sick"]),
        ],
        id="full day tag can coexist with other segments",
    ),
    tt_test_case(
        [["1985-05-24", "8:00"], ["8:00"]],
        [
            (parse("1985-05-24 08:00:00"), None, []),
            (parse("1985-05-25 08:00:00"), None, []),
        ],
        id="dont close too old segment dbgnow",
    ),
    # tt_test_case(
    #     [["9:00", "-", "+3h", "@prio1"], ["11:00"]],
    #     [
    #         (parse("1985-05-25 09:00:00"), parse("1985-05-25 12:00:00"), []),
    #         (parse("1985-05-25 12:00:00"), None, []),
    #     ],
    #     id="move previous end, different prios",
    # ),
]


@pytest.mark.parametrize("partial_functions, expected_start_end_times", ADD_TEST_CASES)
@freeze_time_at_1985_05_25__15_34_12
def test_add_segment(
    db: DatabaseConnection,
    partial_functions,
    expected_start_end_times,
):
    for func in partial_functions:
        func(db=db, report_settings=default_report_settings)
    all_segments = db.get_all_segments()
    start_and_end_times = [
        (segment.start, segment.end, sorted(segment.tags)) for segment in all_segments
    ]
    for observed, expected in zip_longest(
        sorted(start_and_end_times), sorted(expected_start_end_times)
    ):
        print(f"{observed=}")
        print(f"{expected=}")
        print()
    assert sorted(start_and_end_times) == sorted(expected_start_end_times)


LIST_SEGMENTS_TESTS = [
    pytest.param(
        [],
        [
            date(1985, 5, 25),
        ],
        id="no time args",
    ),
    pytest.param(
        None,
        [
            date(1985, 5, 25),
        ],
        id="no time args",
    ),
    pytest.param(
        ["week"],
        [
            date(1985, 5, 20),
            date(1985, 5, 21),
            date(1985, 5, 22),
            date(1985, 5, 23),
            date(1985, 5, 24),
            date(1985, 5, 25),
            date(1985, 5, 26),
        ],
        id="week",
    ),
]


@pytest.mark.parametrize("query, expected_days", LIST_SEGMENTS_TESTS)
@freeze_time_at_1985_05_25__15_34_12
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


def make_partials(input_args):
    """
    Helper to prepare a list of partial functions for timeturner operations.
    Each element can be a tuple (func_name, args) or just args (uses 'add').
    """
    prepared_partials = []
    for maybe_args in input_args:
        if isinstance(maybe_args, tuple):
            func_name, args = maybe_args
        else:
            func_name = "add"
            args = maybe_args
        func = getattr(timeturner, func_name)
        prepared_partials.append(partial(func, args))
    return prepared_partials


def tt_list_segments_case(
    input_args: list[list[str] | tuple[str, list[str]]],
    list_args: list[str] | None,
    test_conditions: list,
    id: str,
):
    """
    Helper to create a pytest parameterized test case for timeturner.list_ high-level logic.

    Args:
        input_args: List of argument lists or tuples for segment creation.
        list_args: Arguments for timeturner.list_.
        test_conditions: List of callables that take the summaries and return True if the test passes.
        id: The pytest case id.
    """
    return pytest.param(
        make_partials(input_args),
        list_args,
        test_conditions,
        id=id,
    )


LIST_SEGMENTS_SUMMARY_TESTS = [
    tt_list_segments_case(
        [
            ["7:30", "-", "+5h"],
            ["@sick"],
        ],
        ["1d"],
        [
            lambda summaries: len(summaries) == 1,
            lambda summaries: summaries[0].summary.over_time == timedelta(hours=0),
        ],
        "no negative overtime when sick during work",
    ),
    tt_list_segments_case(
        [
            ["9:00", "-", "+3h"],
            ["13:00", "-", "+2h"],
        ],
        ["1d"],
        [
            lambda summaries: len(summaries) == 1,
            lambda summaries: sum(len(day.segments) for day in summaries) == 2,
            lambda summaries: summaries[0].summary.work_time.total_seconds()
            == 5 * 3600,
        ],
        "two work segments, correct total work time",
    ),
]


@pytest.mark.parametrize(
    "partial_functions, list_args, test_conditions", LIST_SEGMENTS_SUMMARY_TESTS
)
@freeze_time_at(day=23)
def test_list_segments_summary(db, partial_functions, list_args, test_conditions):
    report_settings = ReportSettings()

    for func in partial_functions:
        func(db=db, report_settings=default_report_settings)

    summaries = timeturner.list_(
        list_args,
        report_settings=report_settings,
        db=db,
    )

    for cond in test_conditions:
        assert cond(summaries), f"Test condition failed: {cond.__doc__ or cond}"
