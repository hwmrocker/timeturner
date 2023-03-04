import sqlite3
from itertools import combinations

import pytest
from pendulum.datetime import DateTime

from timetracker.db import DatabaseConnection, PensiveRow


@pytest.fixture
def db():
    return DatabaseConnection(":memory:")


@pytest.mark.dependency(name="add_slot")
def test_add_slot(db):
    assert db.add_slot(DateTime(1985, 5, 25, 0, 0, 0)) == 1
    rows = db.connection.execute("SELECT * FROM pensieve").fetchall()
    assert len(rows) == 1
    assert rows[0] == (1, "1985-05-25T00:00:00", None, 0, None, None)


def test_add_slot_with_end(db):
    db.add_slot(DateTime(1985, 5, 25, 0, 0, 0), DateTime(1985, 5, 25, 1, 0, 0))
    rows = db.connection.execute("SELECT * FROM pensieve").fetchall()
    assert len(rows) == 1
    assert rows[0] == (1, "1985-05-25T00:00:00", "1985-05-25T01:00:00", 0, None, None)


def test_get_latest_slot(db):
    db.add_slot(DateTime(1985, 5, 25, 0, 0, 0))
    db.add_slot(DateTime(1985, 5, 25, 1, 0, 0))
    row = db.get_latest_slot()
    assert row == PensiveRow(
        pk=2,
        start=DateTime(1985, 5, 25, 1, 0, 0),
        end=None,
        passive=False,
        tags=None,
        description=None,
    )


def _get_all_combinations_of_slots():
    possible_elements = [
        ("end", DateTime(1985, 5, 25, 1, 0, 0)),
        ("passive", True),
        ("tags", "tag1"),
        ("description", "description1"),
    ]
    for i in range(len(possible_elements)):
        for combination in combinations(possible_elements, i + 1):
            yield (dict(combination), dict(combination))


GET_LATEST_TEST_CASES = [
    *_get_all_combinations_of_slots(),
    pytest.param(dict(passive=True), dict(passive=True), id="passive True"),
    pytest.param(dict(passive=False), dict(passive=False), id="passive False"),
    pytest.param(dict(passive=None), dict(passive=False), id="passive None"),
]


@pytest.mark.dependency(name="get_latest", depends=["add_slot"])
@pytest.mark.parametrize("elements, expected_row", GET_LATEST_TEST_CASES)
def test_add_slot_and_get_latest(db, elements, expected_row):
    db.add_slot(
        DateTime(1985, 5, 25, 0, 0, 0),
        **elements,
    )
    expected = PensiveRow(
        pk=1,
        start=DateTime(1985, 5, 25, 0, 0, 0),
        end=expected_row.get("end"),
        passive=expected_row.get("passive", False),
        tags=expected_row.get("tags"),
        description=expected_row.get("description"),
    )
    latest_slot = db.get_latest_slot()
    assert latest_slot == expected


UPDATE_SLOT_TEST_CASES = [
    pytest.param(
        dict(start=DateTime(1985, 5, 25, 0, 0, 0)),
        dict(
            start=DateTime(1985, 5, 25, 1, 0, 0),
            end=DateTime(1985, 5, 25, 2, 0, 0),
            passive=True,
            tags="tag1",
            description="description1",
        ),
        PensiveRow(
            pk=1,
            start=DateTime(1985, 5, 25, 1, 0, 0),
            end=DateTime(1985, 5, 25, 2, 0, 0),
            passive=True,
            tags="tag1",
            description="description1",
        ),
        id="update all fields",
    ),
    pytest.param(
        dict(
            start=DateTime(1985, 5, 25, 1, 0, 0),
            end=DateTime(1985, 5, 25, 2, 0, 0),
            passive=True,
            tags="tag1",
            description="description1",
        ),
        dict(start=DateTime(1985, 5, 25, 0, 0, 0)),
        PensiveRow(
            pk=1,
            start=DateTime(1985, 5, 25, 0, 0, 0),
            end=DateTime(1985, 5, 25, 2, 0, 0),
            passive=True,
            tags="tag1",
            description="description1",
        ),
        id="only change one field",
    ),
    pytest.param(
        dict(
            start=DateTime(1985, 5, 25, 0, 0, 0),
            end=DateTime(1985, 5, 25, 2, 0, 0),
            passive=True,
            tags="tag1",
            description="description1",
        ),
        dict(
            end=None,
            passive=None,
            tags=None,
            description=None,
        ),
        PensiveRow(
            pk=1,
            start=DateTime(1985, 5, 25, 0, 0, 0),
            end=None,
            passive=False,
            tags=None,
            description=None,
        ),
        id="delete all optional fields",
    ),
]


@pytest.mark.dependency(depends=["get_latest"])
@pytest.mark.parametrize("initial_slot, updated_slot, expected", UPDATE_SLOT_TEST_CASES)
def test_update_slot(db, initial_slot, updated_slot, expected):
    pk = db.add_slot(**initial_slot)
    db.update_slot(
        pk,
        **updated_slot,
    )
    row = db.get_latest_slot()
    assert row == expected


def test_delete_slot(db):
    pk = db.add_slot(DateTime(1985, 5, 25, 0, 0, 0))
    rows = db.connection.execute("SELECT * FROM pensieve").fetchall()
    assert len(rows) == 1
    db.delete_slot(pk)
    rows = db.connection.execute("SELECT * FROM pensieve").fetchall()
    assert len(rows) == 0


GET_SLOTS_BETWEEN_TEST_CASES = [
    pytest.param(
        DateTime(1985, 5, 24, 0, 0, 0),
        DateTime(1985, 5, 24, 23, 59, 59),
        [1, 2],
        id="2 on the same day",
    ),
    pytest.param(
        DateTime(1985, 5, 25, 0, 0, 0),
        DateTime(1985, 5, 25, 23, 59, 59),
        [3, 4],
        id="one event ends the next day",
    ),
    pytest.param(
        DateTime(1985, 5, 26, 0, 0, 0),
        DateTime(1985, 5, 26, 23, 59, 59),
        [4, 5],
        id="one event starts the previous day, the other has no end",
    ),
    pytest.param(
        DateTime(1985, 5, 27, 0, 0, 0),
        DateTime(1985, 5, 27, 23, 59, 59),
        [5],
        id="one event starts the previous day, the other has no end",
    ),
]


@pytest.mark.parametrize("start, end, expected", GET_SLOTS_BETWEEN_TEST_CASES)
@pytest.mark.dependency(depends=["add_slot"])
def test_get_slots_between(db, start, end, expected):
    # 2 slots on the same day
    db.add_slot(
        start=DateTime(1985, 5, 24, 7, 0, 0),
        end=DateTime(1985, 5, 24, 12, 0, 0),
    )
    db.add_slot(
        start=DateTime(1985, 5, 24, 13, 0, 0),
        end=DateTime(1985, 5, 24, 17, 0, 0),
    )
    # 1 slot on the next day
    db.add_slot(
        start=DateTime(1985, 5, 25, 9, 0, 0),
        end=DateTime(1985, 5, 25, 17, 0, 0),
    )
    # 1 passive slot ending on the next day
    db.add_slot(
        start=DateTime(1985, 5, 25, 23, 0, 0),
        end=DateTime(1985, 5, 26, 4, 0, 0),
        passive=True,
    )
    db.add_slot(
        start=DateTime(1985, 5, 26, 9, 0, 0),
    )

    rows = db.get_slots_between(start, end)
    assert [row.pk for row in rows] == expected


def test_get_all_slots(db):
    db.add_slot(
        start=DateTime(1985, 5, 24, 7, 0, 0),
        end=DateTime(1985, 5, 24, 12, 0, 0),
    )
    db.add_slot(
        start=DateTime(1985, 5, 24, 13, 0, 0),
        end=DateTime(1985, 5, 24, 17, 0, 0),
    )
    db.add_slot(
        start=DateTime(1985, 5, 25, 9, 0, 0),
        end=DateTime(1985, 5, 25, 17, 0, 0),
    )
    db.add_slot(
        start=DateTime(1985, 5, 25, 23, 0, 0),
        end=DateTime(1985, 5, 26, 4, 0, 0),
        passive=True,
    )
    db.add_slot(
        start=DateTime(1985, 5, 26, 9, 0, 0),
    )

    rows = db.get_all_slots()
    assert len(rows) == 5
