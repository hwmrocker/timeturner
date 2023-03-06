from datetime import date
from pathlib import Path
from typing import Optional

import typer
from pydantic.json import pydantic_encoder
from rich.console import Console

from timeturner import timeturner
from timeturner.db import DatabaseConnection, PensiveRow, TimeSlot
from timeturner.loader import import_text

app = typer.Typer()

console = Console()
print = console.print


@app.command("l", hidden=True)
@app.command("list")
def _list(time: Optional[list[str]] = typer.Argument(None)):
    console.print_json(data=timeturner._list(time), default=pydantic_encoder)


@app.command("a", hidden=True)
@app.command()
def add(
    time: Optional[list[str]] = typer.Argument(None),
    auto_stop: Optional[bool] = None,
    # passive: bool | None = False,
    # tags: str | None = None,
    # description: str | None = None,
):
    console.print_json(data=timeturner.add(time), default=pydantic_encoder)


@app.command("e", hidden=True)
@app.command("end")
def end(
    time: Optional[list[str]] = typer.Argument(None),
):
    console.print_json(data=timeturner.end(time), default=pydantic_encoder)


@app.command("i", hidden=True)
@app.command(name="import")
def import_(text_file: Path):
    db = DatabaseConnection()
    console.print_json(data=import_text(db, text_file), default=pydantic_encoder)


def entrypoint():
    app()


if __name__ == "__main__":
    entrypoint()