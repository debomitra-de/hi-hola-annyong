from pathlib import Path


def repository_root() -> Path:
    """Return the repository root for manual diagnostics and test fixtures."""
    return Path(__file__).resolve().parents[1]


def fixture_path(*parts: str) -> Path:
    return repository_root().joinpath("tests", "fixtures", *parts)
