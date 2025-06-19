import tomlkit

from timeturner import __VERSION__


def test_version():
    pyproject = tomlkit.parse(open("pyproject.toml").read())
    assert __VERSION__ == pyproject["project"]["version"]  # type: ignore


def test_changelog_version_matches_pyproject():
    """
    Ensure the latest released version in the CHANGELOG matches the version in pyproject.toml.
    """
    import re

    # Read CHANGELOG
    with open("CHANGELOG", encoding="utf-8") as f:
        changelog = f.read()

    # Find all released versions (not unreleased)
    matches = re.findall(
        r"^## (\d+\.\d+\.\d+) \((?!unreleased)[^)]+\)", changelog, re.MULTILINE
    )
    assert matches, "No released versions found in CHANGELOG"

    latest_released_version = matches[0]

    # Read pyproject.toml
    pyproject = tomlkit.parse(open("pyproject.toml").read())
    pyproject_version = pyproject["project"]["version"]  # type: ignore

    assert latest_released_version == pyproject_version, (
        f"Latest released version in CHANGELOG ({latest_released_version}) "
        f"does not match pyproject.toml version ({pyproject_version})"
    )
