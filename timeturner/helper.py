from typing import Iterator, cast

from pendulum import period
from pendulum.date import Date
from pendulum.datetime import DateTime


def iter_over_days(start: DateTime, end: DateTime) -> Iterator[Date]:
    for dt in period(start.start_of("day"), end.start_of("day")).range("days"):
        yield cast(DateTime, dt).date()
