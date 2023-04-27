import pytest
from pendulum.date import Date
from pendulum.time import Time

from tests.helpers import parse
from timeturner import models, timeturner
from timeturner.models import DayType, NewSegmentParams, PensiveRow
from timeturner.settings import ReportSettings

GET_SUMMARY_TEST_CASES = [
    pytest.param(
        [],
        models.DailySummary(
            day=Date(1985, 5, 25),
            day_type=DayType.WEEKEND,
            work_time=timeturner.Duration(),
            break_time=timeturner.Duration(),
            start=None,
            end=None,
        ),
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
        models.DailySummary(
            day=Date(1985, 5, 25),
            day_type=DayType.WEEKEND,
            work_time=timeturner.Duration(hours=1),
            break_time=timeturner.Duration(),
            over_time=timeturner.Duration(hours=1),
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
        models.DailySummary(
            day=Date(1985, 5, 25),
            day_type=DayType.WEEKEND,
            work_time=timeturner.Duration(hours=2),
            break_time=timeturner.Duration(),
            over_time=timeturner.Duration(hours=2),
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
        models.DailySummary(
            day=Date(1985, 5, 25),
            day_type=DayType.WEEKEND,
            work_time=timeturner.Duration(hours=2),
            break_time=timeturner.Duration(),
            over_time=timeturner.Duration(hours=2),
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
        models.DailySummary(
            day=Date(1985, 5, 25),
            day_type=DayType.WEEKEND,
            work_time=timeturner.Duration(hours=1, minutes=59),
            break_time=timeturner.Duration(hours=1, minutes=1),
            over_time=timeturner.Duration(hours=1, minutes=59),
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
        models.DailySummary(
            day=Date(1985, 5, 25),
            day_type=DayType.WEEKEND,
            work_time=timeturner.Duration(hours=8, minutes=0),
            break_time=timeturner.Duration(hours=1, minutes=0),
            over_time=timeturner.Duration(hours=8, minutes=0),
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
        models.DailySummary(
            day=Date(1985, 5, 25),
            day_type=DayType.WEEKEND,
            work_time=timeturner.Duration(hours=8, minutes=15),
            break_time=timeturner.Duration(minutes=45),
            over_time=timeturner.Duration(hours=8, minutes=15),
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
        models.DailySummary(
            day=Date(1985, 5, 25),
            day_type=DayType.WEEKEND,
            work_time=timeturner.Duration(hours=4, minutes=45),
            break_time=timeturner.Duration(minutes=15),
            over_time=timeturner.Duration(hours=4, minutes=45),
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
        models.DailySummary(
            day=Date(1985, 5, 25),
            day_type=DayType.WEEKEND,
            work_time=timeturner.Duration(hours=4, minutes=30),
            break_time=timeturner.Duration(minutes=30),
            over_time=timeturner.Duration(hours=4, minutes=30),
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
        models.DailySummary(
            day=Date(1985, 5, 25),
            day_type=DayType.WEEKEND,
            work_time=timeturner.Duration(hours=4, minutes=30),
            break_time=timeturner.Duration(minutes=30),
            over_time=timeturner.Duration(hours=4, minutes=30),
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
    pytest.param(
        [
            PensiveRow(
                pk=1,
                start=parse("1985-05-27"),
                end=parse("1985-05-28"),
                tags=["sick"],
            ),
        ],
        models.DailySummary(
            day=Date(1985, 5, 27),
            day_type=DayType.WORK,
            work_time=timeturner.Duration(),
            break_time=timeturner.Duration(),
            over_time=timeturner.Duration(),
            start=Time(0, 0),
            end=Time(0, 0),
            by_tag={"sick": timeturner.Duration(hours=24)},
        ),
        id="sick day",
    ),
    pytest.param(
        [
            PensiveRow(
                pk=1,
                start=parse("1985-05-27 09:00"),
                end=parse("1985-05-27 10:00"),
                tags=["travel"],
            ),
        ],
        models.DailySummary(
            day=Date(1985, 5, 27),
            day_type=DayType.WORK,
            work_time=timeturner.Duration(hours=1),
            break_time=timeturner.Duration(),
            over_time=timeturner.Duration(hours=-7),
            start=Time(9, 0),
            end=Time(10, 0),
            by_tag={"travel": timeturner.Duration(hours=1)},
        ),
        id="one hour travel",
    ),
    pytest.param(
        [
            PensiveRow(
                pk=1,
                start=parse("1985-05-27 09:00"),
                end=parse("1985-05-27 10:00"),
                tags=["travel"],
            ),
            PensiveRow(
                pk=2,
                start=parse("1985-05-27 12:00"),
                end=parse("1985-05-27 15:00"),
                tags=[],
            ),
        ],
        models.DailySummary(
            day=Date(1985, 5, 27),
            day_type=DayType.WORK,
            work_time=timeturner.Duration(hours=4),
            break_time=timeturner.Duration(hours=2),
            over_time=timeturner.Duration(hours=-4),
            start=Time(9, 0),
            end=Time(15, 0),
            by_tag={"travel": timeturner.Duration(hours=1)},
        ),
        id="one hour travel, 3 hours work",
    ),
    pytest.param(
        [
            PensiveRow(
                pk=1,
                start=parse("1985-05-27 00:00"),
                end=parse("1985-05-27 10:00"),
                tags=["travel"],
            ),
            PensiveRow(
                pk=2,
                start=parse("1985-05-27 12:00"),
                end=parse("1985-05-27 15:00"),
                tags=[],
            ),
        ],
        models.DailySummary(
            day=Date(1985, 5, 27),
            day_type=DayType.WORK,
            work_time=timeturner.Duration(hours=10),
            break_time=timeturner.Duration(hours=2),
            over_time=timeturner.Duration(hours=2),
            start=Time(0, 0),
            end=Time(15, 0),
            by_tag={"travel": timeturner.Duration(hours=10)},
        ),
        id="10 hour travel, 3 hours work",
    ),
    pytest.param(
        [
            PensiveRow(
                pk=1,
                start=parse("1985-05-27 00:00"),
                end=parse("1985-05-27 04:00"),
                tags=["travel"],
            ),
            PensiveRow(
                pk=2,
                start=parse("1985-05-27 12:00"),
                end=parse("1985-05-27 22:00"),
                tags=[],
            ),
        ],
        models.DailySummary(
            day=Date(1985, 5, 27),
            day_type=DayType.WORK,
            work_time=timeturner.Duration(hours=10),
            break_time=timeturner.Duration(hours=8),
            over_time=timeturner.Duration(hours=2),
            start=Time(0, 0),
            end=Time(22, 0),
            by_tag={"travel": timeturner.Duration(hours=4)},
        ),
        id="4 hour travel, 10 hours work",
    ),
    pytest.param(
        [
            PensiveRow(
                pk=1,
                start=parse("1985-05-27 00:00"),
                end=parse("1985-05-27 04:00"),
                tags=["travel"],
            ),
            PensiveRow(
                pk=2,
                start=parse("1985-05-27 12:00"),
                end=parse("1985-05-27 23:00"),
                tags=[],
            ),
        ],
        models.DailySummary(
            day=Date(1985, 5, 27),
            day_type=DayType.WORK,
            work_time=timeturner.Duration(hours=11),
            break_time=timeturner.Duration(hours=8),
            over_time=timeturner.Duration(hours=3),
            start=Time(0, 0),
            end=Time(23, 0),
            by_tag={"travel": timeturner.Duration(hours=4)},
        ),
        id="4 hour travel, 10 hours work",
    ),
]


@pytest.mark.parametrize("segments, expected_summary", GET_SUMMARY_TEST_CASES)
def test_get_summary(segments, expected_summary):
    day = Date(1985, 5, 25)
    if segments:
        day = segments[0].start.date()
    assert (
        timeturner.get_daily_summary(day, segments, report_settings=ReportSettings())
        == expected_summary
    )


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
        timeturner.get_daily_summary(
            Date(1985, 5, 25), segments, report_settings=ReportSettings()
        )


GROUP_BY_DAY_TEST_CASES = [
    pytest.param(
        [],
        {},
        id="empty",
    ),
    pytest.param(
        [
            PensiveRow(
                pk=1,
                start=parse("1985-05-25 00:00:00"),
            ),
        ],
        {
            Date(1985, 5, 25): [
                PensiveRow(
                    pk=1,
                    start=parse("1985-05-25 00:00:00"),
                ),
            ],
        },
        id="one segment",
    ),
    pytest.param(
        [
            PensiveRow(
                pk=1,
                start=parse("1985-05-25 00:00:00"),
            ),
            PensiveRow(
                pk=1,
                start=parse("1985-05-26 00:00:00"),
            ),
        ],
        {
            Date(1985, 5, 25): [
                PensiveRow(
                    pk=1,
                    start=parse("1985-05-25 00:00:00"),
                ),
            ],
            Date(1985, 5, 26): [
                PensiveRow(
                    pk=1,
                    start=parse("1985-05-26 00:00:00"),
                ),
            ],
        },
        id="two segments, different days",
    ),
    pytest.param(
        [
            PensiveRow(
                pk=1,
                start=parse("1985-05-25 00:00:00"),
            ),
            PensiveRow(
                pk=1,
                start=parse("1985-05-25 01:00:00"),
            ),
            PensiveRow(
                pk=1,
                start=parse("1985-05-26 00:00:00"),
            ),
        ],
        {
            Date(1985, 5, 25): [
                PensiveRow(
                    pk=1,
                    start=parse("1985-05-25 00:00:00"),
                ),
                PensiveRow(
                    pk=1,
                    start=parse("1985-05-25 01:00:00"),
                ),
            ],
            Date(1985, 5, 26): [
                PensiveRow(
                    pk=1,
                    start=parse("1985-05-26 00:00:00"),
                ),
            ],
        },
        id="two segments, different days",
    ),
]


@pytest.mark.parametrize("segments, expected_grouped", GROUP_BY_DAY_TEST_CASES)
def test_group_by_day(segments, expected_grouped):
    assert timeturner.group_by_day(segments) == expected_grouped


SPLIT_PARAMS_BY_WEEKDAY_TEST_CASES = [
    pytest.param(
        parse("1985-05-01"),
        parse("1985-05-02"),
        [
            (parse("1985-05-01"), parse("1985-05-02")),
        ],
        id="one day",
    ),
    pytest.param(
        parse("1985-05-01"),
        parse("1985-05-03"),
        [
            (parse("1985-05-01"), parse("1985-05-03")),
        ],
        id="two days, one segment",
    ),
    pytest.param(
        parse("1985-05-25"),
        parse("1985-05-26"),
        [],
        id="one day, on weekend",
    ),
    pytest.param(
        parse("1985-05-25"),
        parse("1985-05-27"),
        [],
        id="two days, on weekend",
    ),
    pytest.param(
        parse("1985-05-23"),
        parse("1985-05-29"),
        [
            (parse("1985-05-23"), parse("1985-05-25")),
            (parse("1985-05-27"), parse("1985-05-29")),
        ],
        id="two days, on weekend",
    ),
    pytest.param(
        parse("1985-05-23"),
        parse("1985-06-07"),
        [
            (parse("1985-05-23"), parse("1985-05-25")),
            (parse("1985-05-27"), parse("1985-06-01")),
            (parse("1985-06-03"), parse("1985-06-07")),
        ],
        id="two weekends",
    ),
    pytest.param(
        parse("1985-12-25"),
        parse("1986-01-02"),
        [
            (parse("1985-12-25"), parse("1985-12-28")),
            (parse("1985-12-30"), parse("1986-01-02")),
        ],
        id="one weekend, range spans year",
    ),
]


@pytest.mark.parametrize(
    "start, end, expected_start_end_days", SPLIT_PARAMS_BY_WEEKDAY_TEST_CASES
)
def test_split_segment_params_per_weekday(start, end, expected_start_end_days):
    segment_params = NewSegmentParams(
        start=start, end=end, tags=["A"], passive=False, description="B"
    )
    split_params = timeturner.split_segment_params_per_weekday(
        segment_params, report_settings=ReportSettings()
    )
    observed_start_end_days = [(params.start, params.end) for params in split_params]
    assert observed_start_end_days == expected_start_end_days
    assert all(s.tags == segment_params.tags for s in split_params)
    assert all(s.passive == segment_params.passive for s in split_params)
    assert all(s.description == segment_params.description for s in split_params)


SPLIT_SEGMENTS_AT_MIDNIGHT_TESTS = [
    pytest.param(
        [],
        [],
        id="empty list",
    ),
    pytest.param(
        [(parse("1985-05-25 00:00:00"), parse("1985-05-25 01:00:00"))],
        [(parse("1985-05-25 00:00:00"), parse("1985-05-25 01:00:00"))],
        id="one segment, no midnight",
    ),
    pytest.param(
        [
            (parse("1985-05-25 00:00:00"), parse("1985-05-25 01:00:00")),
            (parse("1985-05-26 00:00:00"), parse("1985-05-26 01:00:00")),
        ],
        [
            (parse("1985-05-25 00:00:00"), parse("1985-05-25 01:00:00")),
            (parse("1985-05-26 00:00:00"), parse("1985-05-26 01:00:00")),
        ],
        id="two segments, no midnight",
    ),
    pytest.param(
        [(parse("1985-05-25 00:00:00"), parse("1985-05-26 00:00:00"))],
        [(parse("1985-05-25 00:00:00"), parse("1985-05-26 00:00:00"))],
        id="one segment, full day",
    ),
    pytest.param(
        [(parse("1985-05-25 12:00:00"), parse("1985-05-26 01:00:00"))],
        [
            (parse("1985-05-25 12:00:00"), parse("1985-05-26 00:00:00")),
            (parse("1985-05-26 00:00:00"), parse("1985-05-26 01:00:00")),
        ],
        id="one segment, midnight in middle",
    ),
]


@pytest.mark.parametrize(
    "start_end_list, expected_start_end_times", SPLIT_SEGMENTS_AT_MIDNIGHT_TESTS
)
def test_split_segments_at_midnight(start_end_list, expected_start_end_times):
    pensive_rows = []
    for idx, (start, end) in enumerate(start_end_list):
        pensive_rows.append(
            PensiveRow(
                pk=idx,
                start=start,
                end=end,
            )
        )
    observed_start_end_times = [
        (row.start, row.end)
        for row in timeturner.split_segments_at_midnight(pensive_rows)
    ]

    assert observed_start_end_times == expected_start_end_times
