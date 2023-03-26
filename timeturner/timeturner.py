from itertools import groupby
from pathlib import Path
from typing import Iterator

from pendulum.date import Date

from timeturner import loader
from timeturner.db import DatabaseConnection, PensiveRow
from timeturner.parser import parse_args, parse_list_args


def group_by_day(rows: list[PensiveRow]) -> dict[Date, list[PensiveRow]]:
    return {k: list(v) for k, v in groupby(rows, lambda r: r.start.date())}


def _list(
    time: list[str] | None,
    *,
    db: DatabaseConnection,
) -> list[PensiveRow]:
    if time is None:
        time = []
    slots_per_day = {}
    start, end = parse_list_args(time)
    for day in (end - start).range("days"):
        slots_per_day[day.date()] = []
    rows = db.get_slots_between(start, end)
    for day, segments in groupby(rows, lambda r: r.start.date()):
        slots_per_day[day] = list(segments)
    return [
        dict(day=d, weekday=d.weekday(), segments=s) for d, s in slots_per_day.items()
    ]


def add(
    time: list[str] | None,
    *,
    db: DatabaseConnection,
) -> PensiveRow:
    if time is None:
        time = []
    start, end = parse_args(time)
    return db.add_slot(start, end)


def end(
    time: list[str] | None,
    *,
    db: DatabaseConnection,
) -> PensiveRow | None:
    if time is None:
        time = []
    end = parse_args(time, single_time=True)
    last_entry = db.get_latest_slot()

    if last_entry is None:
        raise ValueError("No entries to stop")
    if last_entry.end is not None:
        raise ValueError(f"Last entry already ended {last_entry.end!r}")
    pk = last_entry.pk
    db.update_slot(pk, end=end)
    entry = db.get_slot(pk)
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
