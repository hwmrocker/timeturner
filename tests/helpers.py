from datetime import datetime

from freezegun import freeze_time

from timeturner.helper import get_tz_offset, local_tz, parse

test_now = datetime(1985, 5, 25, 15, 34, 12, tzinfo=local_tz)

freeze_time_at_1985_05_25__15_34_12 = freeze_time(
    test_now.strftime("%Y-%m-%d %H:%M:%S"),
    tz_offset=get_tz_offset(test_now),
)  # Saturday


def freeze_time_at(year=1985, month=5, day=25, hour=15, minute=34, second=12):
    test_now = datetime(year, month, day, hour, minute, second, tzinfo=local_tz)
    return freeze_time(
        test_now.strftime("%Y-%m-%d %H:%M:%S"),
        tz_offset=get_tz_offset(test_now),
    )


parse = parse
