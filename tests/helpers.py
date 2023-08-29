from typing import cast

from freezegun import freeze_time
from pendulum.datetime import DateTime
from pendulum.parser import parse as _parse


def parse(date_string) -> DateTime:
    """Parse a date string using pendulum but adding the local timezone."""
    return cast(DateTime, _parse(date_string, tz="local"))


freeze_time_at_1985_25_05__15_34_12 = freeze_time(
    "1985-05-25 15:34:12",
    tz_offset=-int(parse("1985-05-25 15:34:12").offset_hours),  # type: ignore
)

test_now = parse("1985-05-25 15:34:12")
