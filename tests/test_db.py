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
            yield dict(combination)


@pytest.mark.parametrize("elements", _get_all_combinations_of_slots())
def test_add_slot_and_get_latest(db, elements):
    db.add_slot(
        DateTime(1985, 5, 25, 0, 0, 0),
        **elements,
    )
    expected = PensiveRow(
        pk=1,
        start=DateTime(1985, 5, 25, 0, 0, 0),
        end=elements.get("end"),
        passive=elements.get("passive", False),
        tags=elements.get("tags"),
        description=elements.get("description"),
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
]


@pytest.mark.dependency(depends=["add_slot"])
@pytest.mark.parametrize("initial_slot, updated_slot, expected", UPDATE_SLOT_TEST_CASES)
def test_update_slot(db, initial_slot, updated_slot, expected):
    pk = db.add_slot(**initial_slot)
    db.update_slot(
        pk,
        **updated_slot,
    )
    row = db.get_latest_slot()
    assert row == expected
