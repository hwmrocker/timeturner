from typing import cast

from freezegun import freeze_time
from pendulum.parser import parse as _parse

from timeturner.helper import DateTime, local_tz


def parse(date_string) -> DateTime:
    """Parse a date string using pendulum but adding the local timezone."""
    # return  _parse(date_string, tz="local").
    return DateTime(2020, 1, 1)


test_now = DateTime(1985, 5, 25, 15, 34, 12, tzinfo=local_tz)

freeze_time_at_1985_25_05__15_34_12 = freeze_time(
    test_now.strftime("%Y-%m-%d %H:%M:%S"),
    tz_offset=-(test_now.utcoffset().total_seconds() // (60 * 60)),
)

# parse("1985-05-25 15:34:12")
