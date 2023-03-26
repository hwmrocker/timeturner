from pathlib import Path
from typing import cast

import pytest
from pendulum.datetime import DateTime
from pendulum.parser import parse as _parse

from timeturner import loader
from timeturner.db import DatabaseConnection, TimeSegment


def parse(s: str) -> DateTime:
    return cast(DateTime, _parse(s, strict=False))


SINGLE_TIME_SEGMENT_DATA = [
    pytest.param(
        "2023-01-02 08:30 | 2023-01-02 09:00 | 30min    | install system              | setup\n",
        [
            TimeSegment(
                start=parse("2023-01-02 08:30"),
                end=parse("2023-01-02 09:00"),
                tags=None,
                description="setup@install system",
                passive=False,
            )
        ],
        id="single segment, one line",
    ),
    pytest.param(
        """2023-01-02 09:00 | 2023-01-02 11:20 | 2h 20min | basics                      | setup
    Setup Git, jira, outlook, ... mit sergiy
    #pair
""",
        [
            TimeSegment(
                start=parse("2023-01-02 09:00"),
                end=parse("2023-01-02 11:20"),
                tags=["pair"],
                description="setup@basics\nSetup Git, jira, outlook, ... mit sergiy",
                passive=False,
            )
        ],
        id="single segment, multiple lines",
    ),
    pytest.param(
        """2023-01-02 13:30 | 2023-01-02 15:00 | 1h 30min | setup                       | setup
    docker, hr
""",
        [
            TimeSegment(
                start=parse("2023-01-02 13:30"),
                end=parse("2023-01-02 15:00"),
                tags=None,
                description="setup@setup\ndocker, hr",
                passive=False,
            )
        ],
        id="single segment, multiple lines, no tags",
    ),
    pytest.param(
        "2023-02-16 23:15 | 2023-02-17 07:45 | 8h 30min |                             | travel\n",
        [
            TimeSegment(
                start=parse("2023-02-16 23:15"),
                end=parse("2023-02-17 07:45"),
                tags=None,
                description="travel@",
                passive=True,
            ),
        ],
        id="single segment, passive",
    ),
]


@pytest.mark.parametrize("lines, expected", SINGLE_TIME_SEGMENT_DATA)
def test_extract_segments(lines, expected):
    assert list(loader.extract_segments(lines.splitlines())) == expected


IMPORT_TEXT_DATA = [
    pytest.param(Path("tests/data/hamster-report.txt"), 12, id="hamster-list.txt"),
    pytest.param(Path("tests/data/empty-hamster-report.txt"), 0, id="hamster-list.txt"),
]


@pytest.mark.parametrize("file, expected_records", IMPORT_TEXT_DATA)
def test_import_file(db: DatabaseConnection, file, expected_records):
    for event in loader.import_text(db, file):
        print(event)

    assert len(db.get_all_segments()) == expected_records


def test_import_file_with_empty_file(db: DatabaseConnection):
    with pytest.raises(ValueError):
        for event in loader.import_text(db, Path("tests/data/empty_file.txt")):
            print(event)
