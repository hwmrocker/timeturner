from itertools import combinations

import pytest

from tests.helpers import parse, test_now
from timeturner.db import DatabaseConnection
from timeturner.models import PensiveRow

pytestmark = pytest.mark.dependency(name="db_tests")

dt_850525 = test_now.replace(hour=0, minute=0, second=0, microsecond=0)


@pytest.mark.dependency(name="add_segment")
def test_add_segment(db: DatabaseConnection):
    start_date = dt_850525
    assert db.add_segment(start_date).pk == 1
    rows = db.connection.execute("SELECT * FROM pensieve").fetchall()
    assert len(rows) == 1
    assert rows[0] == (1, str(start_date), None, 0, None)


def test_add_segment_with_end(db: DatabaseConnection):
    db.add_segment(
        dt_850525,
        dt_850525.replace(hour=1),
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
        dt_850525,
        dt_850525.replace(hour=1),
        0,
        None,
    )

    assert db_entry == expected


GET_LATEST_TEST_CASES = [
    pytest.param(
        [
            dt_850525,
            dt_850525.replace(hour=1),
        ],
        2,
        id="two segments in order",
    ),
    pytest.param(
        [
            dt_850525.replace(hour=1),
            dt_850525,
        ],
        1,
        id="two segments in reverse order",
    ),
    pytest.param(
        [
            dt_850525,
            dt_850525.replace(hour=2),
            dt_850525.replace(hour=1),
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
        ("end", dt_850525.replace(hour=1)),
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
        dt_850525,
        **elements,
    )
    expected = PensiveRow(
        pk=1,
        start=dt_850525,
        end=expected_row.get("end"),
        passive=expected_row.get("passive", False),
        tags=expected_row.get("tags", []),
        description=expected_row.get("description"),
    )
    latest_segment = db.get_latest_segment()
    assert latest_segment == expected


UPDATE_SEGMENTS_TEST_CASES = [
    pytest.param(
        dict(start=dt_850525),
        dict(
            start=dt_850525.replace(hour=1),
            end=dt_850525.replace(hour=2),
            passive=True,
            tags=["tag1"],
            description="description1",
        ),
        PensiveRow(
            pk=1,
            start=dt_850525.replace(hour=1),
            end=dt_850525.replace(hour=2),
            passive=True,
            tags=["tag1"],
            description="description1",
        ),
        id="update all fields",
    ),
    pytest.param(
        dict(
            start=dt_850525.replace(hour=1),
            end=dt_850525.replace(hour=2),
            passive=True,
            tags=["tag1"],
            description="description1",
        ),
        dict(start=dt_850525),
        PensiveRow(
            pk=1,
            start=dt_850525,
            end=dt_850525.replace(hour=2),
            passive=True,
            tags=["tag1"],
            description="description1",
        ),
        id="only change one field",
    ),
    pytest.param(
        dict(
            start=dt_850525,
            end=dt_850525.replace(hour=2),
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
            start=dt_850525,
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
    pk = db.add_segment(dt_850525).pk
    rows = db.connection.execute("SELECT * FROM pensieve").fetchall()
    assert len(rows) == 1
    db.delete_segment(pk)
    rows = db.connection.execute("SELECT * FROM pensieve").fetchall()
    assert len(rows) == 0


GET_SEGMENTS_BETWEEN_TEST_CASES = [
    pytest.param(
        dt_850525.replace(day=24),
        dt_850525.replace(day=24, hour=23, minute=59, second=59),
        [1, 2],
        id="2 on the same day",
    ),
    pytest.param(
        dt_850525,
        dt_850525.replace(hour=23, minute=59, second=59),
        [3, 4],
        id="one event ends the next day",
    ),
    pytest.param(
        dt_850525.replace(day=26),
        dt_850525.replace(day=26, hour=23, minute=59, second=59),
        [4, 5],
        id="one event starts the previous day, the other has no end",
    ),
    pytest.param(
        dt_850525.replace(day=27),
        dt_850525.replace(day=27, hour=23, minute=59, second=59),
        [5],
        id="one event starts the previous day, the other has no end",
    ),
]


@pytest.mark.parametrize("start, end, expected", GET_SEGMENTS_BETWEEN_TEST_CASES)
@pytest.mark.dependency(depends=["add_segment"])
def test_get_segments_between(db: DatabaseConnection, start, end, expected):
    # 2 segments on the same day
    db.add_segment(
        start=dt_850525.replace(day=24, hour=7),
        end=dt_850525.replace(day=24, hour=12),
    )
    db.add_segment(
        start=dt_850525.replace(day=24, hour=13),
        end=dt_850525.replace(day=24, hour=17),
    )
    # 1 segment on the next day
    db.add_segment(
        start=dt_850525.replace(hour=9),
        end=dt_850525.replace(hour=17),
    )
    # 1 passive segment ending on the next day
    db.add_segment(
        start=dt_850525.replace(hour=23),
        end=dt_850525.replace(day=26, hour=4),
        passive=True,
    )
    db.add_segment(
        start=dt_850525.replace(day=26, hour=9),
    )

    rows = db.get_segments_between(start, end)
    assert [row.pk for row in rows] == expected


def test_get_segments_between_full_day_corner_case(db: DatabaseConnection):
    db.add_segment(
        start=dt_850525.replace(day=1),
        end=dt_850525.replace(day=2),
        tags=["holiday"],
    )
    db.add_segment(
        start=dt_850525.replace(day=2),
        end=dt_850525.replace(day=3),
        tags=["vacation"],
    )
    rows = db.get_segments_between(
        dt_850525.replace(day=2),
        dt_850525.replace(day=4),
    )
    assert [row.pk for row in rows] == [2]


def test_get_all_segments(db: DatabaseConnection):
    db.add_segment(
        start=dt_850525.replace(day=24, hour=7),
        end=dt_850525.replace(day=24, hour=12),
    )
    db.add_segment(
        start=dt_850525.replace(day=24, hour=13),
        end=dt_850525.replace(day=24, hour=17),
    )
    db.add_segment(
        start=dt_850525.replace(hour=9),
        end=dt_850525.replace(hour=17),
    )
    db.add_segment(
        start=dt_850525.replace(hour=23),
        end=dt_850525.replace(day=26, hour=4),
        passive=True,
    )
    db.add_segment(
        start=dt_850525.replace(day=26, hour=9),
    )

    rows = db.get_all_segments()
    assert len(rows) == 5
