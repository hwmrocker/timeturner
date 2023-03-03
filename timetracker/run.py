from rich.console import Console
from rich.traceback import install
from typer import run

install(show_locals=True)
console = Console()
print = console.print


def main():
    print("Hello, world!")


def entrypoint():
    run(main)


if __name__ == "__main__":
    entrypoint()
