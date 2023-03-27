from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from pydantic.json import pydantic_encoder
from rich.console import Console

from timeturner import rich_output, timeturner
from timeturner.settings import TimeTurnerSettings

app = typer.Typer()

console = Console()
print = console.print
settings = TimeTurnerSettings()


class Output(str, Enum):
    json = "json"
    rich = "rich"


@app.callback(no_args_is_help=True)
def callback(
    output: Optional[Output] = None,
):
    global settings
    additional_settings_args = dict()
    if output is not None:
        additional_settings_args["output"] = output
    if additional_settings_args:
        settings = TimeTurnerSettings(**additional_settings_args)


@app.command("l", hidden=True)
@app.command("list")
def _list(time: Optional[list[str]] = typer.Argument(None)):
    data = timeturner._list(time, db=settings.database.connection)
    if settings.output == "json":
        console.print_json(data=data, default=pydantic_encoder)
    else:
        rich_output.segments_by_day(data)


@app.command("a", hidden=True)
@app.command()
def add(
    time: Optional[list[str]] = typer.Argument(None),
    auto_stop: Optional[bool] = None,
    # passive: bool | None = False,
    # tags: str | None = None,
    # description: str | None = None,
):
    data = timeturner.add(time, db=settings.database.connection)
    if settings.output == "json":
        console.print_json(data=data, default=pydantic_encoder)
    else:
        rich_output.print_pretty_record(data)


@app.command("e", hidden=True)
@app.command("end")
def end(
    time: Optional[list[str]] = typer.Argument(None),
):
    data = timeturner.end(time, db=settings.database.connection)
    console.print_json(data=data, default=pydantic_encoder)


@app.command("i", hidden=True)
@app.command(name="import")
def import_(text_file: Path):
    data = list(timeturner.import_json(text_file, db=settings.database.connection))
    console.print_json(data=data, default=pydantic_encoder)


@app.command("c", hidden=True)
@app.command(name="config")
def config():
    console.print_json(data=settings, default=pydantic_encoder)


def entrypoint():
    app()


if __name__ == "__main__":
    entrypoint()
