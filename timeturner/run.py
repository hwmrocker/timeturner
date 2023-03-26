from pathlib import Path
from typing import Optional

import typer
from pydantic.json import pydantic_encoder
from rich.console import Console

from timeturner import rich_output, timeturner
from timeturner.db import DatabaseConnection
from timeturner.settings import settings

app = typer.Typer()

console = Console()
print = console.print


@app.command("l", hidden=True)
@app.command("list")
def _list(time: Optional[list[str]] = typer.Argument(None)):
    data = timeturner._list(time)
    if settings.output == "json":
        console.print_json(data=data, default=pydantic_encoder)
    else:
        rich_output.print_pretty_list(data)


@app.command("a", hidden=True)
@app.command()
def add(
    time: Optional[list[str]] = typer.Argument(None),
    auto_stop: Optional[bool] = None,
    # passive: bool | None = False,
    # tags: str | None = None,
    # description: str | None = None,
):
    data = timeturner.add(time)
    if settings.output == "json":
        console.print_json(data=data, default=pydantic_encoder)
    else:
        rich_output.print_pretty_record(data)


@app.command("e", hidden=True)
@app.command("end")
def end(
    time: Optional[list[str]] = typer.Argument(None),
):
    console.print_json(data=timeturner.end(time), default=pydantic_encoder)


@app.command("i", hidden=True)
@app.command(name="import")
def import_(text_file: Path):
    db = settings.database.connection
    console.print_json(
        data=list(timeturner.import_json(db, text_file)), default=pydantic_encoder
    )


@app.command("c", hidden=True)
@app.command(name="config")
def config():
    console.print_json(data=settings, default=pydantic_encoder)


def entrypoint():
    app()


if __name__ == "__main__":
    entrypoint()
