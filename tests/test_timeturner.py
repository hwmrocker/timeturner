from datetime import date, datetime, time

import holidays
import pytest

from tests.helpers import parse
from timeturner import models, timeturner
from timeturner.db import DatabaseConnection
from timeturner.models import DayType, NewSegmentParams, PensiveRow
from timeturner.settings import ReportSettings


def segment_matches(segment: PensiveRow, expected: dict) -> bool:
    """
    Check if a segment matches the expected dict (partial match).
    """
    for key, value in expected.items():
        if not hasattr(segment, key):
            return False
        seg_val = getattr(segment, key)
        # For datetime/date, allow string or datetime comparison
        if isinstance(seg_val, (datetime, date)) and isinstance(value, str):
            try:
                if isinstance(seg_val, datetime):
                    seg_val_str = seg_val.strftime("%Y-%m-%d")
                else:
                    seg_val_str = str(seg_val)
                if not seg_val_str.startswith(value):
                    return False
            except Exception:
                return False
        elif seg_val != value:
            return False
    return True


def check_segments_in_db(db, expected_segments: list[dict]):
    """
    For each expected segment dict, check that at least one segment in the DB matches.
    """
    all_segments = db.get_all_segments()
    for expected in expected_segments:
        matched = any(segment_matches(seg, expected) for seg in all_segments)
        assert matched, f"Expected segment not found in DB: {expected}"


@pytest.mark.parametrize(
    "precondition,args,precheck,expected",
    [
        pytest.param(
            # No pre-existing segments
            [],
            {"year": 2024, "country": "DE", "subdivision": "BY"},
            [],
            [
                # Expect at least one known Bavarian holiday
                {"description": "Neujahr", "tags": ["holiday"]},
                {"description": "Tag der Deutschen Einheit", "tags": ["holiday"]},
            ],
            id="import_bavarian_holidays",
        ),
        pytest.param(
            # No pre-existing segments, nationwide only
            [],
            {"year": 2024, "country": "DE", "subdivision": None},
            [],
            [
                {"description": "Neujahr", "tags": ["holiday"]},
                # Should not include "Mariä Himmelfahrt" (BY only)
            ],
            id="import_germany_nationwide",
        ),
        pytest.param(
            # Pre-existing segment for Neujahr, should not duplicate
            [
                {
                    "start": datetime(2024, 1, 1),
                    "end": datetime(2024, 1, 2),
                    "tags": ["holiday"],
                    "description": "Neujahr",
                    "full_days": True,
                }
            ],
            {"year": 2024, "country": "DE", "subdivision": "BY"},
            [
                {"description": "Neujahr", "tags": ["holiday"]},
            ],
            [
                {"description": "Neujahr", "tags": ["holiday"]},
                {"description": "Tag der Deutschen Einheit", "tags": ["holiday"]},
            ],
            id="existing_holiday_segment",
        ),
    ],
)
def test_add_holidays(precondition, args, precheck, expected):
    db = DatabaseConnection(":memory:")
    report_settings = ReportSettings()
    # 1. load preconditions
    for seg in precondition:
        db.add_segment(
            seg.get("start"),
            seg.get("end"),
            tags=seg.get("tags", []),
            description=seg.get("description"),
            full_days=seg.get("full_days", False),
        )
    # 2. run precheck
    check_segments_in_db(db, precheck)
    # 3. run add_holidays
    result = timeturner.add_holidays(
        year=args.get("year", 2024),
        country=args.get("country", "DE"),
        subdivision=args.get("subdivision"),
        report_settings=report_settings,
        db=db,
    )
    # 4. run expected checks
    check_segments_in_db(db, expected)


GET_SUMMARY_TEST_CASES = [
    pytest.param(
        [],
        models.DailySummary(
            day=date(1985, 5, 25),
            day_type=DayType.WEEKEND,
            work_time=timeturner.timedelta(),
            break_time=timeturner.timedelta(),
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
            day=date(1985, 5, 25),
            day_type=DayType.WEEKEND,
            work_time=timeturner.timedelta(hours=1),
            break_time=timeturner.timedelta(),
            over_time=timeturner.timedelta(hours=1),
            start=time(0, 0),
            end=time(1, 0),
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
            day=date(1985, 5, 25),
            day_type=DayType.WEEKEND,
            work_time=timeturner.timedelta(hours=2),
            break_time=timeturner.timedelta(),
            over_time=timeturner.timedelta(hours=2),
            start=time(0, 0),
            end=time(2, 0),
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
            day=date(1985, 5, 25),
            day_type=DayType.WEEKEND,
            work_time=timeturner.timedelta(hours=2),
            break_time=timeturner.timedelta(),
            over_time=timeturner.timedelta(hours=2),
            start=time(0, 0),
            end=time(2, 0),
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
            day=date(1985, 5, 25),
            day_type=DayType.WEEKEND,
            work_time=timeturner.timedelta(hours=1, minutes=59),
            break_time=timeturner.timedelta(hours=1, minutes=1),
            over_time=timeturner.timedelta(hours=1, minutes=59),
            start=time(0, 0),
            end=time(3, 0),
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
            day=date(1985, 5, 25),
            day_type=DayType.WEEKEND,
            work_time=timeturner.timedelta(hours=8, minutes=0),
            break_time=timeturner.timedelta(hours=1, minutes=0),
            over_time=timeturner.timedelta(hours=8, minutes=0),
            start=time(0, 0),
            end=time(9, 0),
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
            day=date(1985, 5, 25),
            day_type=DayType.WEEKEND,
            work_time=timeturner.timedelta(hours=8, minutes=15),
            break_time=timeturner.timedelta(minutes=45),
            over_time=timeturner.timedelta(hours=8, minutes=15),
            start=time(0, 0),
            end=time(9, 0),
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
            day=date(1985, 5, 25),
            day_type=DayType.WEEKEND,
            work_time=timeturner.timedelta(hours=4, minutes=45),
            break_time=timeturner.timedelta(minutes=15),
            over_time=timeturner.timedelta(hours=4, minutes=45),
            start=time(0, 0),
            end=time(5, 0),
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
            day=date(1985, 5, 25),
            day_type=DayType.WEEKEND,
            work_time=timeturner.timedelta(hours=4, minutes=30),
            break_time=timeturner.timedelta(minutes=30),
            over_time=timeturner.timedelta(hours=4, minutes=30),
            start=time(0, 0),
            end=time(5, 0),
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
            day=date(1985, 5, 25),
            day_type=DayType.WEEKEND,
            work_time=timeturner.timedelta(hours=4, minutes=30),
            break_time=timeturner.timedelta(minutes=30),
            over_time=timeturner.timedelta(hours=4, minutes=30),
            start=time(0, 0),
            end=time(5, 0),
            by_tag={
                "A": timeturner.timedelta(hours=2),
                "B": timeturner.timedelta(hours=4, minutes=30),
                "C": timeturner.timedelta(hours=2, minutes=30),
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
            day=date(1985, 5, 27),
            day_type=DayType.WORK,
            work_time=timeturner.timedelta(),
            break_time=timeturner.timedelta(),
            over_time=timeturner.timedelta(),
            start=time(0, 0),
            end=time(0, 0),
            by_tag={"sick": timeturner.timedelta(hours=24)},
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
            day=date(1985, 5, 27),
            day_type=DayType.WORK,
            work_time=timeturner.timedelta(hours=1),
            break_time=timeturner.timedelta(),
            over_time=timeturner.timedelta(hours=-7),
            start=time(9, 0),
            end=time(10, 0),
            by_tag={"travel": timeturner.timedelta(hours=1)},
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
            day=date(1985, 5, 27),
            day_type=DayType.WORK,
            work_time=timeturner.timedelta(hours=4),
            break_time=timeturner.timedelta(hours=2),
            over_time=timeturner.timedelta(hours=-4),
            start=time(9, 0),
            end=time(15, 0),
            by_tag={"travel": timeturner.timedelta(hours=1)},
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
            day=date(1985, 5, 27),
            day_type=DayType.WORK,
            work_time=timeturner.timedelta(hours=10),
            break_time=timeturner.timedelta(hours=2),
            over_time=timeturner.timedelta(hours=2),
            start=time(0, 0),
            end=time(15, 0),
            by_tag={"travel": timeturner.timedelta(hours=10)},
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
            day=date(1985, 5, 27),
            day_type=DayType.WORK,
            work_time=timeturner.timedelta(hours=10),
            break_time=timeturner.timedelta(hours=8),
            over_time=timeturner.timedelta(hours=2),
            start=time(0, 0),
            end=time(22, 0),
            by_tag={"travel": timeturner.timedelta(hours=4)},
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
            day=date(1985, 5, 27),
            day_type=DayType.WORK,
            work_time=timeturner.timedelta(hours=11),
            break_time=timeturner.timedelta(hours=8),
            over_time=timeturner.timedelta(hours=3),
            start=time(0, 0),
            end=time(23, 0),
            by_tag={"travel": timeturner.timedelta(hours=4)},
        ),
        id="4 hour travel, 10 hours work",
    ),
]


@pytest.mark.parametrize("segments, expected_summary", GET_SUMMARY_TEST_CASES)
def test_get_summary(segments, expected_summary):
    day = date(1985, 5, 25)
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
            date(1985, 5, 25), segments, report_settings=ReportSettings()
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
            date(1985, 5, 25): [
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
            date(1985, 5, 25): [
                PensiveRow(
                    pk=1,
                    start=parse("1985-05-25 00:00:00"),
                ),
            ],
            date(1985, 5, 26): [
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
            date(1985, 5, 25): [
                PensiveRow(
                    pk=1,
                    start=parse("1985-05-25 00:00:00"),
                ),
                PensiveRow(
                    pk=1,
                    start=parse("1985-05-25 01:00:00"),
                ),
            ],
            date(1985, 5, 26): [
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
