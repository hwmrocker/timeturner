import tomlkit

from timeturner import __VERSION__


def test_version():
    pyproject = tomlkit.parse(open("pyproject.toml").read())
    assert __VERSION__ == pyproject["project"]["version"]  # type: ignore
