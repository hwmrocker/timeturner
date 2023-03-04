from typing import Optional

import typer
from rich.console import Console
from rich.traceback import install

from timetracker.db import DatabaseConnection, PensiveRow, TimeSlot
from timetracker.parser import parse_args

app = typer.Typer()

console = Console()
# install(show_locals=True, console=console)
print = console.print


@app.command("list")
def _list(time: Optional[list[str]] = typer.Argument(None)):
    if time is None:
        time = []
    start, end = parse_args(time, prefer_full_days=True)
    print(start, end)
    db = DatabaseConnection()
    rows = db.get_slots_between(start, end)
    for row in rows:
        print(row)


@app.command()
def add(
    time: list[str],
    # passive: bool | None = False,
    # tags: str | None = None,
    # description: str | None = None,
):
    start, end = parse_args(time)
    # print(start, end)
    db = DatabaseConnection()
    db.add_slot(
        start,
        end,
        #     passive,
        #     tags,
        #     description,
    )


def entrypoint():
    app()


if __name__ == "__main__":
    entrypoint()
