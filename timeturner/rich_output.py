from pendulum.duration import Duration
from rich import box
from rich.console import Console
from rich.table import Table

from timeturner.models import PensiveRow, SegmentsByDay

console = Console()


def _pretty_duration(duration: Duration) -> str:
    a = ""
    if duration.seconds < 0:
        # return "NEGATIVE TIME"
        a = "-"

    periods = [
        # ("w", duration.weeks),
        # ("d", duration.remaining_days),
        ("h", int(duration.total_hours())),
        ("m", duration.minutes),
    ]

    parts = []
    for period in periods:
        unit, count = period
        if abs(count) > 0:
            parts.append(f"{abs(count)}{unit}")

    return a + str(" ".join(parts))


def pretty_duration(duration: Duration, breaks: Duration = Duration()) -> str:
    if breaks:
        return f"{_pretty_duration(duration)} (+{_pretty_duration(breaks)} break)"
    return _pretty_duration(duration)


def segments_by_day(
    segments: list[SegmentsByDay],
    show_all: bool = False,
) -> None:
    table = Table(
        title="Segments",
        show_header=True,
        header_style="bold magenta",
        show_lines=True,
        box=box.SIMPLE,
    )

    table.add_column("Start", style="dim", width=20)
    table.add_column("End", style="dim", width=6)
    table.add_column("Type", style="dim", width=6)
    table.add_column("Work Time", style="dim", width=8)
    table.add_column("Break Time", style="dim", width=8)
    table.add_column("Over Time", style="dim", width=8)
    table.add_column("Tags", style="dim", width=20)

    total_work = []
    total_break = []
    total_over = []
    w = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for segment in segments:
        total_work.append(segment.summary.work_time)
        total_break.append(segment.summary.break_time)
        total_over.append(segment.summary.over_time)
        if segment.summary.start:
            start_str = (
                f"[bold]{w[segment.day.weekday()]}[/] {segment.day} "
                f"{segment.summary.start.format('HH:mm')}"
            )
        else:
            start_str = f"[bold]{w[segment.day.weekday()]}[/] {segment.day}"
        table.add_row(
            start_str,
            segment.summary.end.format("HH:mm") if segment.summary.end else "",
            str(segment.summary.day_type.value),
            pretty_duration(segment.summary.work_time),
            pretty_duration(segment.summary.break_time),
            pretty_duration(segment.summary.over_time),
            ", ".join(segment.tags),
        )
        if show_all:
            for sub_segment in segment.segments:
                start_str: str = (
                    (" " * 15 + f"[white]{sub_segment.start.format('HH:mm')}[/]")
                    if sub_segment.start
                    else ""
                )
                table.add_row(
                    start_str,
                    sub_segment.end.format("HH:mm") if sub_segment.end else "",
                    "work" if not sub_segment.passive else "break",
                    pretty_duration(sub_segment.duration),
                    "",
                    "",
                    ", ".join(sub_segment.tags),
                )
                start_str = ""
    table.add_row(
        "total:",
        "",
        "",
        pretty_duration(sum(total_work, Duration())),  # type: ignore
        pretty_duration(sum(total_break, Duration())),  # type: ignore
        pretty_duration(sum(total_over, Duration())),  # type: ignore
    )

    console.print(table)
    # total_duration = sum(total_durations, Duration())
    # print(f"Total: {total_duration.total_hours():.0f}h {total_duration.minutes}m")


def print_pretty_record(segment: PensiveRow | None) -> None:
    if segment is None:
        console.print("No segment found.")
        return

    print(f"Added record with start: {segment.start.format('YYYY-MM-DD HH:mm')}")
