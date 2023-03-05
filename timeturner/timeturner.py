import json

from pydantic.json import pydantic_encoder

from timeturner.db import DatabaseConnection, PensiveRow
from timeturner.parser import parse_args


def _list(time: list[str] | None) -> list[PensiveRow]:
    if time is None:
        time = []
    start, end = parse_args(time, prefer_full_days=True)
    print(start, end)
    db = DatabaseConnection()
    rows = db.get_slots_between(start, end)
    return [row for row in rows]


def add(time: list[str] | None) -> PensiveRow | None:
    if time is None:
        time = []
    start, end = parse_args(time)
    db = DatabaseConnection()
    pk = db.add_slot(start, end)
    entry = db.get_slot(pk)
    return entry


def stop(time: list[str] | None) -> PensiveRow | None:
    if time is None:
        time = []
    end = parse_args(time, single_time=True)
    db = DatabaseConnection()
    last_entry = db.get_latest_slot()

    if last_entry is None:
        raise ValueError("No entries to stop")
    if last_entry.end is not None:
        raise ValueError(f"Last entry already ended {last_entry.end!r}")
    pk = last_entry.pk
    db.update_slot(pk, end=end)
    entry = db.get_slot(pk)
    return entry
