import re
from pathlib import Path
from typing import Iterator, cast

from pendulum.datetime import DateTime
from pendulum.parser import parse

from timeturner.db import DatabaseConnection, TimeSlot

re_date = re.compile(r"^\d{4}-\d{2}-\d{2}")


def extract_time_slots(lines: list[str]) -> Iterator[TimeSlot]:
    time_slot = None
    for line in lines:
        line = line.strip()

        if line[0].isdigit():
            # this is a new time slot
            if time_slot is not None:
                yield time_slot
        elif line[0] == "#":
            # this is a continuation of the previous time slot
            if time_slot is None:
                raise ValueError("Continuation without time slot")
            time_slot.tags = line[1:].strip()
            continue
        else:
            # this is a continuation of the previous time slot
            if time_slot is None:
                raise ValueError("Continuation without time slot")
            if time_slot.description is None:
                time_slot.description = line
            else:
                time_slot.description += f"\n{line}"
            continue

        # split the line into columns
        columns = line.split("|")

        # remove the whitespace
        columns = [c.strip() for c in columns]

        # parse the start and end date
        start = cast(DateTime, parse(columns[0]))
        end = cast(DateTime, parse(columns[1])) if columns[1] else None

        # duration is not used
        # columns[2]

        # parse the activity
        activity = columns[3]

        # parse the tags
        category = columns[4]

        # build the TimeSlot object

        time_slot = TimeSlot(
            start=start,
            end=end,
            passive=category == "travel",
            tags=None,
            description=f"{category}@{activity}",
        )

    if time_slot is not None:
        yield time_slot


def import_text(db: DatabaseConnection, text_file: Path) -> Iterator[TimeSlot]:

    table_separator = "-" * 80 + "\n"

    with text_file.open() as f:
        lines = f.readlines()

    # find the table separator
    try:
        index = lines.index(table_separator)
    except ValueError:
        raise ValueError(f"Could not find table separator {table_separator}")

    # remove the header
    lines = lines[index + 1 :]

    # remove the footer
    lines = lines[: lines.index(table_separator)]

    for entry in extract_time_slots(lines):
        db.add_slot(**entry.dict())
        yield entry
