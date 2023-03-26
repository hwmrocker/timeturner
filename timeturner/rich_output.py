from pendulum.duration import Duration
from rich import box
from rich.console import Console
from rich.table import Table

from timeturner.db import PensiveRow

console = Console()


def _pretty_duration(duration: Duration) -> str:
    if duration.seconds < 0:
        return "NEGATIVE TIME"

    periods = [
        ("w", duration.weeks),
        ("d", duration.remaining_days),
        ("h", duration.hours),
        ("m", duration.minutes),
    ]

    parts = []
    for period in periods:
        unit, count = period
        if abs(count) > 0:
            parts.append(f"{count}{unit}")

    return str(" ".join(parts))


def account_for_breaks(duration: Duration) -> tuple[Duration, int]:
    # Nach 4h Arbeitszeit: 15 Minuten
    # Nach 6:15h Arbeitszeit: weitere 30 Minuten.
    if duration.total_minutes() > (6 * 60 + 15):
        duration_without_breaks = duration - Duration(minutes=45)
        return duration_without_breaks, 45

    elif duration.total_minutes() > (4 * 60):
        duration_without_breaks = duration - Duration(minutes=15)
        return duration_without_breaks, 15
    return duration, 0


def pretty_duration(duration: Duration, breaks: int) -> str:
    if breaks:
        return f"{_pretty_duration(duration)} (+{breaks}m break)"
    return _pretty_duration(duration)


def print_pretty_list(segments: list[PensiveRow]) -> None:
    table = Table(
        title="Segments",
        show_header=True,
        header_style="bold magenta",
        show_lines=True,
        box=box.SIMPLE,
    )

    table.add_column("Start", style="dim", width=20)
    table.add_column("End", style="dim", width=20)
    table.add_column("Duration", style="dim", width=20)
    table.add_column("Description", style="dim", width=20)

    total_durations = []

    for segment in segments:
        actual_duration, breaks = account_for_breaks(segment.duration)
        total_durations.append(actual_duration)
        table.add_row(
            segment.start.format("YYYY-MM-DD HH:mm"),
            segment.end.time().isoformat() if segment.end else "",
            pretty_duration(actual_duration, breaks),
            segment.description,
        )

    console.print(table)
    total_duration = sum(total_durations, Duration())
    print(f"Total: {total_duration.total_hours():.0f}h {total_duration.minutes}m")


def print_pretty_record(segment: PensiveRow | None) -> None:
    if segment is None:
        console.print("No segment found.")
        return

    print(f"Added record with start: {segment.start.format('YYYY-MM-DD HH:mm')}")
