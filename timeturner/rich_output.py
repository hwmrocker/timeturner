from pendulum.duration import Duration
from rich import box
from rich.console import Console
from rich.table import Table

from timeturner.db import PensiveRow
from timeturner.timeturner import SegmentsByDay

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


def pretty_duration(duration: Duration, breaks: Duration) -> str:
    if breaks:
        return f"{_pretty_duration(duration)} (+{_pretty_duration(breaks)} break)"
    return _pretty_duration(duration)


def segments_by_day(segments: list[SegmentsByDay]) -> None:
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

    total_durations = []

    for segment in segments:
        total_durations.append(segment.summary.work_time)
        if segment.summary.start:
            start_str = f"{segment.day} {segment.summary.start.format('HH:mm')}"
        else:
            start_str = f"{segment.day}"
        table.add_row(
            start_str,
            segment.summary.end.format("HH:mm") if segment.summary.end else "",
            pretty_duration(segment.summary.work_time, segment.summary.break_time),
        )

    console.print(table)
    total_duration = sum(total_durations, Duration())
    print(f"Total: {total_duration.total_hours():.0f}h {total_duration.minutes}m")


def print_pretty_record(segment: PensiveRow | None) -> None:
    if segment is None:
        console.print("No segment found.")
        return

    print(f"Added record with start: {segment.start.format('YYYY-MM-DD HH:mm')}")
