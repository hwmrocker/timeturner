from itertools import groupby
from pathlib import Path
from typing import Iterator, cast

from pendulum import period
from pendulum.date import Date
from pendulum.datetime import DateTime
from pendulum.duration import Duration

from timeturner import loader
from timeturner.db import DatabaseConnection
from timeturner.helper import iter_over_days
from timeturner.models import (
    DailySummary,
    DayType,
    NewSegmentParams,
    PensiveRow,
    SegmentsByDay,
)
from timeturner.parser import parse_add_args, parse_list_args, single_time_parse
from timeturner.settings import ReportSettings
from timeturner.tools.boltons_iterutils import pairwise_iter


def get_daily_summary(
    day: Date,
    segments: list[PensiveRow],
    *,
    report_settings: ReportSettings,
) -> DailySummary:
    """
    Expecting segments to be sorted by start time.
    All segments should be on the same day.
    No segments should overlap.

    get daily work time
    get daily break time
    get daily overtime

    vacation and holiday are not considered work time and produce no overtime
    """
    work_time = Duration()
    break_time = Duration()
    start = None
    end = None
    by_tag = {}
    segment = None
    for segment in segments:
        if segment.start.date() != day:
            raise ValueError(
                f"Segment is not on the given day. {day} != {segment.start.date()}"
            )
        if report_settings.holiday_tag in segment.tags:
            return DailySummary(
                day=day,
                day_type=DayType.HOLIDAY,
                work_time=Duration(),
                break_time=Duration(),
                over_time=Duration(),
                start=None,
                end=None,
                description="Holiday",
                by_tag={},
            )
        if start is None:
            start = segment.start.time()
        work_time += segment.duration
        for tag in segment.tags:
            if tag not in by_tag:
                by_tag[tag] = Duration()
            by_tag[tag] += segment.duration

    if segment and segment.end is not None:
        end = segment.end.time()
    for segment, next_segment in pairwise_iter(segments):
        if segment.end is None:
            raise ValueError(
                "Segment has no end time but is followed by another segment."
            )
        new_break = cast(Duration, next_segment.start - segment.end)
        if new_break > Duration(minutes=1):
            break_time += new_break
        else:
            # Short breaks are not counted as breaks.
            work_time += new_break

    if work_time > Duration(hours=6, minutes=15):
        if break_time < Duration(minutes=45):
            missing_break_time = Duration(minutes=45) - break_time
            work_time -= missing_break_time
            break_time += missing_break_time
    elif work_time > Duration(hours=4):
        if break_time < Duration(minutes=15):
            missing_break_time = Duration(minutes=15) - break_time
            work_time -= missing_break_time
            break_time += missing_break_time

    required_work_duration = Duration(hours=8)
    day_type = DayType.WORK
    if day.weekday() >= 5:
        required_work_duration = Duration(hours=0)
        day_type = DayType.WEEKEND

    return DailySummary(
        day=day,
        day_type=day_type,
        work_time=work_time,
        break_time=break_time,
        over_time=work_time - required_work_duration,
        start=start,
        end=end,
        by_tag=by_tag,
    )


def group_by_day(rows: list[PensiveRow]) -> dict[Date, list[PensiveRow]]:
    return {k: list(v) for k, v in groupby(rows, lambda r: r.start.date())}


def split_segments_at_midnight(rows: list[PensiveRow]) -> Iterator[PensiveRow]:
    for row in rows:
        if row.end and row.end.date() == row.start.date():
            yield row
        elif not row.end:
            yield row
        else:
            yield PensiveRow(
                pk=row.pk,
                start=row.start,
                end=row.start.end_of("day"),
                tags=row.tags,
                description=row.description,
                passive=row.passive,
            )
            for day in iter_over_days(row.start.add(days=1), row.end):
                if day == row.end.date():
                    end = row.end
                else:
                    end = day.end_of("day")
                print(f"day: {day.start_of('day')}, end: {end}")
                yield PensiveRow(
                    pk=row.pk,
                    start=DateTime(day.year, day.month, day.day, tzinfo=row.start.tz),
                    end=end,
                    tags=row.tags,
                    description=row.description,
                    passive=row.passive,
                )


def list_(
    time: list[str] | None,
    *,
    report_settings: ReportSettings,
    db: DatabaseConnection,
) -> list[SegmentsByDay]:
    if time is None:
        time = []
    segments_per_day = {}
    start, end = parse_list_args(time)
    for day in iter_over_days(start, end):
        segments_per_day[str(day)] = []
    rows = db.get_segments_between(start, end)
    midnight_devided_segments = list(split_segments_at_midnight(rows))
    for day, segments in groupby(midnight_devided_segments, lambda r: r.start.date()):
        segments_per_day[str(day)] = list(segments)
    daily_segments = []
    for day in iter_over_days(start, end):
        # request_period.range("days"):
        day = cast(DateTime, day)
        segments = segments_per_day[str(day)]
        daily_segments.append(
            SegmentsByDay(
                day=day,
                weekday=day.weekday(),
                segments=segments,
                summary=get_daily_summary(
                    day,
                    segments,
                    report_settings=report_settings,
                ),
            )
        )
    return daily_segments


def add(
    time: list[str] | None,
    *,
    holiday: bool = False,
    report_settings: ReportSettings,
    db: DatabaseConnection,
) -> PensiveRow:
    prefer_full_days = False
    now = DateTime.now()

    if time is None:
        time = []
    new_segment_params = parse_add_args(
        time,
        prefer_full_days=prefer_full_days,
        holiday=holiday,
        report_settings=report_settings,
    )
    start, end = new_segment_params.start, new_segment_params.end

    conflicting_segments = db.get_segments_between(start, end)
    for current_segment in conflicting_segments:
        # TODO: return a warning that other segments were changed
        if start < current_segment.start:
            if end and end > current_segment.start:
                if current_segment.end and end < current_segment.end:
                    db.update_segment(current_segment.pk, start=end)
                elif current_segment.end and end >= current_segment.end:
                    db.delete_segment(current_segment.pk)
                else:
                    db.update_segment(current_segment.pk, start=end)
            elif end is None and current_segment.start < now:
                new_segment_params.end = current_segment.start
        elif current_segment.end is None:
            db.update_segment(current_segment.pk, end=start)
        elif end and start > current_segment.start and end < current_segment.end:
            db.update_segment(current_segment.pk, end=start)
            ret = db.add_segment(**new_segment_params.dict())
            db.add_segment(
                end,
                current_segment.end,
                tags=current_segment.tags,
                description=current_segment.description,
                passive=current_segment.passive,
            )
            return ret
        elif start < current_segment.end and start > current_segment.start:
            db.update_segment(current_segment.pk, end=start)

    return db.add_segment(**new_segment_params.dict())


def end(
    time: list[str] | None,
    *,
    report_settings: ReportSettings,
    db: DatabaseConnection,
) -> PensiveRow | None:
    if time is None:
        time = []
    end = single_time_parse(time)
    last_entry = db.get_latest_segment()

    if last_entry is None:
        raise ValueError("No entries to stop")
    if last_entry.end is not None:
        raise ValueError(f"Last entry already ended {last_entry.end!r}")
    pk = last_entry.pk
    db.update_segment(pk, end=end)
    entry = db.get_segment(pk)
    return entry


def import_text(
    path: Path,
    *,
    db: DatabaseConnection,
) -> Iterator[PensiveRow]:
    return loader.import_text(db, path)


def import_json(
    path: Path,
    *,
    report_settings: ReportSettings,
    db: DatabaseConnection,
) -> Iterator[PensiveRow]:
    del report_settings
    return loader.import_json(db, path)
