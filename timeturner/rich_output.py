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


def pretty_duration(duration: Duration) -> str:
    # Nach 4h Arbeitszeit: 15 Minuten
    # Nach 6:15h Arbeitszeit: weitere 30 Minuten.
    if duration.total_minutes() > (6 * 60 + 15):
        duration_without_breaks = duration - Duration(minutes=45)
        return f"{_pretty_duration(duration_without_breaks)} (with 45m break)"

    elif duration.total_minutes() > (4 * 60):
        duration_without_breaks = duration - Duration(minutes=15)
        return f"{_pretty_duration(duration_without_breaks)} (with 15m break)"
    return _pretty_duration(duration)


def print_pretty_list(time_slots: list[PensiveRow]) -> None:
    table = Table(
        title="Time Slots",
        show_header=True,
        header_style="bold magenta",
        show_lines=True,
        box=box.SIMPLE,
    )

    table.add_column("Start", style="dim", width=20)
    table.add_column("End", style="dim", width=20)
    table.add_column("Duration", style="dim", width=20)
    table.add_column("Description", style="dim", width=20)

    for slot in time_slots:
        table.add_row(
            slot.start.format("YYYY-MM-DD HH:mm"),
            slot.end.time().isoformat() if slot.end else "",
            pretty_duration(slot.duration),
            slot.description,
        )

    console.print(table)


def print_pretty_record(time_slot: PensiveRow | None) -> None:
    if time_slot is None:
        console.print("No time slot found.")
        return

    print(f"Added record with start: {time_slot.start.format('YYYY-MM-DD HH:mm')}")
