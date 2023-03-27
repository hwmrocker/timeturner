from itertools import combinations

import pytest
from pendulum import datetime

# from pendulum.datetime import DateTime
from pendulum.parser import parse

from timeturner.db import DatabaseConnection, PensiveRow

pytestmark = pytest.mark.dependency(name="db_tests")


@pytest.mark.dependency(name="add_segment")
def test_add_segment(db: DatabaseConnection):
    start_date = datetime(1985, 5, 25, 0, 0, 0, tz="local")
    assert db.add_segment(start_date).pk == 1
    rows = db.connection.execute("SELECT * FROM pensieve").fetchall()
    assert len(rows) == 1
    assert rows[0] == (1, str(start_date), None, 0, None)


def test_add_segment_with_end(db: DatabaseConnection):
    db.add_segment(
        datetime(1985, 5, 25, 0, 0, 0, tz="local"),
        datetime(1985, 5, 25, 1, 0, 0, tz="local"),
    )
    rows = db.connection.execute("SELECT * FROM pensieve").fetchall()
    assert len(rows) == 1
    pk, start, end, passive, description = rows[0]

    db_entry = (
        pk,
        parse(start),
        parse(end),
        passive,
        description,
    )
    expected = (
        1,
        datetime(1985, 5, 25, 0, 0, 0, tz="local"),
        datetime(1985, 5, 25, 1, 0, 0, tz="local"),
        0,
        None,
    )

    assert db_entry == expected


GET_LATEST_TEST_CASES = [
    pytest.param(
        [
            datetime(1985, 5, 25, 0, 0, 0, tz="local"),
            datetime(1985, 5, 25, 1, 0, 0, tz="local"),
        ],
        2,
        id="two segments in order",
    ),
    pytest.param(
        [
            datetime(1985, 5, 25, 1, 0, 0, tz="local"),
            datetime(1985, 5, 25, 0, 0, 0, tz="local"),
        ],
        1,
        id="two segments in reverse order",
    ),
    pytest.param(
        [
            datetime(1985, 5, 25, 0, 0, 0, tz="local"),
            datetime(1985, 5, 25, 2, 0, 0, tz="local"),
            datetime(1985, 5, 25, 1, 0, 0, tz="local"),
        ],
        2,
        id="two segments in mixed order",
    ),
]


@pytest.mark.parametrize("db_entries, latest_pk", GET_LATEST_TEST_CASES)
@pytest.mark.dependency(name="get_latest", depends=["add_segment"])
def test_get_latest_segment(db: DatabaseConnection, db_entries, latest_pk):
    for entry in db_entries:
        pk = db.add_segment(entry).pk
        print(f"Added {entry} with pk {pk}")
    row = db.get_latest_segment()
    latest_date = sorted(db_entries)[-1]
    assert row
    assert row.pk == latest_pk
    assert row == PensiveRow(
        pk=latest_pk,
        start=latest_date,
        end=None,
        passive=False,
        tags=[],
        description=None,
    )


def _get_all_combinations_of_segments():
    possible_elements = [
        ("end", datetime(1985, 5, 25, 1, 0, 0, tz="local")),
        ("passive", True),
        ("tags", ["tag1"]),
        ("description", "description1"),
    ]
    for i in range(len(possible_elements)):
        for combination in combinations(possible_elements, i + 1):
            yield (dict(combination), dict(combination))


GET_LATEST_TEST_CASES = [
    *_get_all_combinations_of_segments(),
    pytest.param(dict(passive=True), dict(passive=True), id="passive True"),
    pytest.param(dict(passive=False), dict(passive=False), id="passive False"),
    pytest.param(dict(passive=None), dict(passive=False), id="passive None"),
]


@pytest.mark.dependency(name="get_latest", depends=["add_segment"])
@pytest.mark.parametrize("elements, expected_row", GET_LATEST_TEST_CASES)
def test_add_segment_and_get_latest(db: DatabaseConnection, elements, expected_row):
    db.add_segment(
        datetime(1985, 5, 25, 0, 0, 0, tz="local"),
        **elements,
    )
    expected = PensiveRow(
        pk=1,
        start=datetime(1985, 5, 25, 0, 0, 0, tz="local"),
        end=expected_row.get("end"),
        passive=expected_row.get("passive", False),
        tags=expected_row.get("tags", []),
        description=expected_row.get("description"),
    )
    latest_segment = db.get_latest_segment()
    assert latest_segment == expected


UPDATE_SEGMENTS_TEST_CASES = [
    pytest.param(
        dict(start=datetime(1985, 5, 25, 0, 0, 0, tz="local")),
        dict(
            start=datetime(1985, 5, 25, 1, 0, 0, tz="local"),
            end=datetime(1985, 5, 25, 2, 0, 0, tz="local"),
            passive=True,
            tags=["tag1"],
            description="description1",
        ),
        PensiveRow(
            pk=1,
            start=datetime(1985, 5, 25, 1, 0, 0, tz="local"),
            end=datetime(1985, 5, 25, 2, 0, 0, tz="local"),
            passive=True,
            tags=["tag1"],
            description="description1",
        ),
        id="update all fields",
    ),
    pytest.param(
        dict(
            start=datetime(1985, 5, 25, 1, 0, 0, tz="local"),
            end=datetime(1985, 5, 25, 2, 0, 0, tz="local"),
            passive=True,
            tags=["tag1"],
            description="description1",
        ),
        dict(start=datetime(1985, 5, 25, 0, 0, 0, tz="local")),
        PensiveRow(
            pk=1,
            start=datetime(1985, 5, 25, 0, 0, 0, tz="local"),
            end=datetime(1985, 5, 25, 2, 0, 0, tz="local"),
            passive=True,
            tags=["tag1"],
            description="description1",
        ),
        id="only change one field",
    ),
    pytest.param(
        dict(
            start=datetime(1985, 5, 25, 0, 0, 0, tz="local"),
            end=datetime(1985, 5, 25, 2, 0, 0, tz="local"),
            passive=True,
            tags=["tag1"],
            description="description1",
        ),
        dict(
            end=None,
            passive=None,
            tags=[],
            description=None,
        ),
        PensiveRow(
            pk=1,
            start=datetime(1985, 5, 25, 0, 0, 0, tz="local"),
            end=None,
            passive=False,
            tags=[],
            description=None,
        ),
        id="delete all optional fields",
    ),
]


@pytest.mark.dependency(depends=["get_latest"])
@pytest.mark.parametrize(
    "initial_segment, updated_segment, expected", UPDATE_SEGMENTS_TEST_CASES
)
def test_update_segment(
    db: DatabaseConnection, initial_segment, updated_segment, expected
):
    pk = db.add_segment(**initial_segment).pk
    db.update_segment(
        pk,
        **updated_segment,
    )
    row = db.get_latest_segment()
    assert row == expected


def test_delete_segment(db: DatabaseConnection):
    pk = db.add_segment(datetime(1985, 5, 25, 0, 0, 0, tz="local")).pk
    rows = db.connection.execute("SELECT * FROM pensieve").fetchall()
    assert len(rows) == 1
    db.delete_segment(pk)
    rows = db.connection.execute("SELECT * FROM pensieve").fetchall()
    assert len(rows) == 0


GET_SEGMENTS_BETWEEN_TEST_CASES = [
    pytest.param(
        datetime(1985, 5, 24, 0, 0, 0, tz="local"),
        datetime(1985, 5, 24, 23, 59, 59, tz="local"),
        [1, 2],
        id="2 on the same day",
    ),
    pytest.param(
        datetime(1985, 5, 25, 0, 0, 0, tz="local"),
        datetime(1985, 5, 25, 23, 59, 59, tz="local"),
        [3, 4],
        id="one event ends the next day",
    ),
    pytest.param(
        datetime(1985, 5, 26, 0, 0, 0, tz="local"),
        datetime(1985, 5, 26, 23, 59, 59, tz="local"),
        [4, 5],
        id="one event starts the previous day, the other has no end",
    ),
    pytest.param(
        datetime(1985, 5, 27, 0, 0, 0, tz="local"),
        datetime(1985, 5, 27, 23, 59, 59, tz="local"),
        [5],
        id="one event starts the previous day, the other has no end",
    ),
]


@pytest.mark.parametrize("start, end, expected", GET_SEGMENTS_BETWEEN_TEST_CASES)
@pytest.mark.dependency(depends=["add_segment"])
def test_get_segments_between(db: DatabaseConnection, start, end, expected):
    # 2 segments on the same day
    db.add_segment(
        start=datetime(1985, 5, 24, 7, 0, 0, tz="local"),
        end=datetime(1985, 5, 24, 12, 0, 0, tz="local"),
    )
    db.add_segment(
        start=datetime(1985, 5, 24, 13, 0, 0, tz="local"),
        end=datetime(1985, 5, 24, 17, 0, 0, tz="local"),
    )
    # 1 segment on the next day
    db.add_segment(
        start=datetime(1985, 5, 25, 9, 0, 0, tz="local"),
        end=datetime(1985, 5, 25, 17, 0, 0, tz="local"),
    )
    # 1 passive segment ending on the next day
    db.add_segment(
        start=datetime(1985, 5, 25, 23, 0, 0, tz="local"),
        end=datetime(1985, 5, 26, 4, 0, 0, tz="local"),
        passive=True,
    )
    db.add_segment(
        start=datetime(1985, 5, 26, 9, 0, 0, tz="local"),
    )

    rows = db.get_segments_between(start, end)
    assert [row.pk for row in rows] == expected


def test_get_all_segments(db: DatabaseConnection):
    db.add_segment(
        start=datetime(1985, 5, 24, 7, 0, 0, tz="local"),
        end=datetime(1985, 5, 24, 12, 0, 0, tz="local"),
    )
    db.add_segment(
        start=datetime(1985, 5, 24, 13, 0, 0, tz="local"),
        end=datetime(1985, 5, 24, 17, 0, 0, tz="local"),
    )
    db.add_segment(
        start=datetime(1985, 5, 25, 9, 0, 0, tz="local"),
        end=datetime(1985, 5, 25, 17, 0, 0, tz="local"),
    )
    db.add_segment(
        start=datetime(1985, 5, 25, 23, 0, 0, tz="local"),
        end=datetime(1985, 5, 26, 4, 0, 0, tz="local"),
        passive=True,
    )
    db.add_segment(
        start=datetime(1985, 5, 26, 9, 0, 0, tz="local"),
    )

    rows = db.get_all_segments()
    assert len(rows) == 5
