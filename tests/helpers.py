from datetime import datetime
from typing import cast

from freezegun import freeze_time
from pendulum.parser import parse as _parse

from timeturner.helper import local_tz


def parse(date_string) -> datetime:
    """Parse a date string using pendulum but adding the local timezone."""
    # return  _parse(date_string, tz="local").
    dt = datetime.fromisoformat(date_string)
    return dt.replace(tzinfo=local_tz)
    # return datetime(2020, 1, 1)


test_now = datetime(1985, 5, 25, 15, 34, 12, tzinfo=local_tz)

freeze_time_at_1985_25_05__15_34_12 = freeze_time(
    test_now.strftime("%Y-%m-%d %H:%M:%S"),
    tz_offset=-int(test_now.utcoffset().total_seconds() // (60 * 60)),
)

# parse("1985-05-25 15:34:12")
