from typing import Optional

import typer
from pydantic.json import pydantic_encoder
from rich.console import Console
from rich.traceback import install

from timeturner import timeturner
from timeturner.db import DatabaseConnection, PensiveRow, TimeSlot
from timeturner.parser import parse_args

app = typer.Typer()

console = Console()
# install(show_locals=True, console=console)
print = console.print


@app.command("list")
def _list(time: Optional[list[str]] = typer.Argument(None)):
    console.print_json(data=timeturner._list(time), default=pydantic_encoder)


@app.command()
def add(
    time: Optional[list[str]] = typer.Argument(None),
    # passive: bool | None = False,
    # tags: str | None = None,
    # description: str | None = None,
):
    console.print_json(data=timeturner.add(time), default=pydantic_encoder)


@app.command()
def stop(
    time: Optional[list[str]] = typer.Argument(None),
):
    console.print_json(data=timeturner.stop(time), default=pydantic_encoder)


def entrypoint():
    app()


if __name__ == "__main__":
    entrypoint()
