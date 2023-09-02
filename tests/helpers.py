from datetime import datetime

from freezegun import freeze_time

from timeturner.helper import local_tz, parse

test_now = datetime(1985, 5, 25, 15, 34, 12, tzinfo=local_tz)

freeze_time_at_1985_25_05__15_34_12 = freeze_time(
    test_now.strftime("%Y-%m-%d %H:%M:%S"),
    tz_offset=-int(test_now.utcoffset().total_seconds() // (60 * 60)),
)

parse = parse
