from itertools import groupby
from pathlib import Path
from typing import Iterator, Optional

from pendulum import period
from pendulum.date import Date
from pendulum.duration import Duration
from pendulum.time import Time
from pydantic import BaseModel

from timeturner import loader
from timeturner.db import DatabaseConnection, PensiveRow
from timeturner.parser import parse_args, parse_list_args
from timeturner.tools.boltons_iterutils import pairwise_iter


class DailySummary(BaseModel):
    work_time: Duration
    break_time: Duration
    start: Optional[Time]
    end: Optional[Time]
    by_tag: dict[str, Duration]


class SegmentsByDay(BaseModel):
    day: Date
    weekday: int
    segments: list[PensiveRow]
    summary: DailySummary


def get_summary(segments: list[PensiveRow]) -> DailySummary:
    work_time = Duration()
    break_time = Duration()
    start = None
    end = None
    by_tag = {}
    segment = None
    for segment in segments:
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
            continue
        new_break = next_segment.start - segment.end
        if new_break >= Duration(minutes=1):
            break_time += new_break

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

    return DailySummary(
        work_time=work_time,
        break_time=break_time,
        start=start,
        end=end,
        by_tag=by_tag,
    )


def group_by_day(rows: list[PensiveRow]) -> dict[Date, list[PensiveRow]]:
    return {k: list(v) for k, v in groupby(rows, lambda r: r.start.date())}


def _list(
    time: list[str] | None,
    *,
    db: DatabaseConnection,
) -> list[SegmentsByDay]:
    if time is None:
        time = []
    segments_per_day = {}
    start, end = parse_list_args(time)
    request_period = period(start, end)
    for day in request_period.range("days"):
        segments_per_day[str(day.date())] = []
    rows = db.get_segments_between(start, end)
    for day, segments in groupby(rows, lambda r: r.start.date()):
        segments_per_day[str(day)] = list(segments)
    daily_segments = []
    for day in request_period.range("days"):
        segments = segments_per_day[str(day.date())]
        daily_segments.append(
            SegmentsByDay(
                day=day,
                weekday=day.weekday(),
                segments=segments,
                summary=get_summary(segments),
            )
        )
    return daily_segments


def add(
    time: list[str] | None,
    *,
    db: DatabaseConnection,
) -> PensiveRow:
    if time is None:
        time = []
    start, end = parse_args(time)
    return db.add_segment(start, end)


def end(
    time: list[str] | None,
    *,
    db: DatabaseConnection,
) -> PensiveRow | None:
    if time is None:
        time = []
    end = parse_args(time, single_time=True)
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
    db: DatabaseConnection,
) -> Iterator[PensiveRow]:
    return loader.import_json(db, path)
