import pytest

from tests.helpers import freeze_time_at_1985_25_05__15_34_12, parse
from timeturner import timeturner

pytestmark = pytest.mark.dependency(depends=["db_tests"], scope="session")


@freeze_time_at_1985_25_05__15_34_12
def test_add_slot(db):
    assert timeturner.add(None, db=db).start == parse("1985-05-25 15:34:00")
    assert timeturner.add([], db=db).start == parse("1985-05-25 15:34:00")
