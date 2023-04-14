import re
from pathlib import Path
from typing import Iterator, cast

from pendulum.datetime import DateTime
from pendulum.parser import parse

from timeturner.db import DatabaseConnection
from timeturner.models import PensiveRow, TimeSegment

re_date = re.compile(r"^\d{4}-\d{2}-\d{2}")


def extract_segments(lines: list[str]) -> Iterator[TimeSegment]:
    segment = None
    for line in lines:
        line = line.strip()

        if line[0].isdigit():
            # this is a new segment
            if segment is not None:
                yield segment
        elif line[0] == "#":
            # this is a continuation of the previous segment
            if segment is None:  # pragma: no cover
                raise ValueError("Continuation without segment")
            segment.tags = [e[1:].strip() for e in line.split(",")]
            continue
        else:
            # this is a continuation of the previous segment
            if segment is None:  # pragma: no cover
                raise ValueError("Continuation without segment")
            if segment.description is None:  # pragma: no cover
                segment.description = line
            else:
                segment.description += f"\n{line}"
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

        # build the TimeSegment object

        segment = TimeSegment(
            start=start,
            end=end,
            passive=category == "travel",
            tags=[],
            description=f"{category}@{activity}",
        )

    if segment is not None:
        yield segment


def import_text(db: DatabaseConnection, text_file: Path) -> Iterator[PensiveRow]:
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

    for entry in extract_segments(lines):
        yield db.add_segment(**entry.dict())


def import_json(db: DatabaseConnection, json_file: Path) -> Iterator[PensiveRow]:
    import json

    with json_file.open() as f:
        data = json.load(f)

    for entry in data:
        yield db.add_segment(
            start=entry["start"],
            end=entry["end"],
            passive=entry["passive"],
            tags=entry["tags"],
            description=entry["description"],
        )
