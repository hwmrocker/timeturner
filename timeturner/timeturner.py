from pathlib import Path
from typing import Iterator

from timeturner import loader
from timeturner.db import DatabaseConnection, PensiveRow
from timeturner.parser import parse_args


def _list(
    time: list[str] | None,
    *,
    db: DatabaseConnection = DatabaseConnection(),
) -> list[PensiveRow]:
    if time is None:
        time = []
    start, end = parse_args(time, prefer_full_days=True)
    print(start, end)
    rows = db.get_slots_between(start, end)
    return [row for row in rows]


def add(
    time: list[str] | None,
    *,
    db: DatabaseConnection = DatabaseConnection(),
) -> PensiveRow:
    if time is None:
        time = []
    start, end = parse_args(time)
    return db.add_slot(start, end)


def end(
    time: list[str] | None,
    *,
    db: DatabaseConnection = DatabaseConnection(),
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


def import_text(db: DatabaseConnection, path: Path) -> Iterator[PensiveRow]:
    return loader.import_text(db, path)
