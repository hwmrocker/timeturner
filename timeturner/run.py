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
    if output is not None:
        if output not in ("json", "rich"):
            raise typer.BadParameter("Output must be either 'json' or 'rich'")
        settings.report.output = output


@app.command("l", hidden=True)
@app.command("list")
def _list(
    time: Optional[list[str]] = typer.Argument(None),
    show_all: bool = False,
):
    data = timeturner.list_(
        time,
        report_settings=settings.report,
        db=settings.database.connection,
    )
    if settings.report.output == "json":
        console.print_json(data=data, default=pydantic_encoder)
    else:
        rich_output.segments_by_day(
            data,
            show_all=show_all,
        )


@app.command("a", hidden=True)
@app.command()
def add(
    time: Optional[list[str]] = typer.Argument(None),
    holiday: bool = False,
    auto_stop: Optional[bool] = None,
    # passive: bool | None = False,
    # tags: str | None = None,
    # description: str | None = None,
):
    data = timeturner.add(
        time,
        holiday=holiday,
        report_settings=settings.report,
        db=settings.database.connection,
    )
    if settings.report.output == "json":
        console.print_json(data=data, default=pydantic_encoder)
    else:
        for segment in data:
            rich_output.print_pretty_record(segment)


@app.command("e", hidden=True)
@app.command("end")
def end(
    time: Optional[list[str]] = typer.Argument(None),
):
    data = timeturner.end(
        time,
        report_settings=settings.report,
        db=settings.database.connection,
    )
    console.print_json(data=data, default=pydantic_encoder)


@app.command("i", hidden=True)
@app.command(name="import")
def import_(text_file: Path):
    data = list(
        timeturner.import_json(
            text_file,
            report_settings=settings.report,
            db=settings.database.connection,
        )
    )
    console.print_json(data=data, default=pydantic_encoder)


@app.command("c", hidden=True)
@app.command(name="config")
def config():
    console.print_json(data=settings, default=pydantic_encoder)


def entrypoint():
    app()


if __name__ == "__main__":
    entrypoint()
