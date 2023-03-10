import pytest

from timeturner.db import DatabaseConnection


@pytest.fixture
def db():
    return DatabaseConnection(":memory:")
