"""Офлайн-демонстрация BFS, фильтров и ошибок параметров."""

from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import shlex
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.main import main as program

BASE = ["--package", "is-odd", "--repository",
        "https://registry.npmjs.org", "--version", "3.0.1"]
CATALOGS = {
    "is-odd": {"name": "is-odd", "versions": {"3.0.1": {
        "name": "is-odd", "version": "3.0.1",
        "dependencies": {"is-number": "^6.0.0"}}}},
    "is-number": {"name": "is-number", "versions": {"6.0.0": {
        "name": "is-number", "version": "6.0.0"}}},
}


def fake_catalog(name, repository):
    """Вернуть явно тестовый каталог без сети."""
    return CATALOGS[name]


def run(argv, expected):
    """Показать запуск и проверить код возврата."""
    output, errors = io.StringIO(), io.StringIO()
    print("$ python -m src.main " + shlex.join(argv))
    with patch("src.npm_graph.fetch_catalog", side_effect=fake_catalog):
        with redirect_stdout(output), redirect_stderr(errors):
            try:
                code = program(argv)
            except SystemExit as error:
                code = error.code
    print(output.getvalue(), end="")
    print(errors.getvalue(), end="")
    print(f"Код завершения: {code}\n")
    if code != expected:
        raise SystemExit("Неожиданный код завершения")


def main():
    """Показать различные графы, фильтры и ошибки CLI."""
    print("Офлайн-демонстрация: HTTP-каталоги подменены тестовыми.")
    run(BASE, 0)
    for name in ["chain", "cycle", "diamond", "isolated", "self_cycle"]:
        run(["--package", "A", "--version", "1.0.0", "--test",
             "--repository", f"tests/fixtures/{name}.json"], 0)
    run(["--package", "A", "--version", "1.0.0", "--test",
         "--repository", "tests/fixtures/diamond.json", "--filter", "B"], 0)
    cases = [["--package", "bad name"], ["--repository", "bad"],
             ["--test", "yes"], ["--version", "latest"],
             ["--output", "graph.png"], ["--ascii", "yes"],
             ["--filter", "   "]]
    for extra in cases:
        run(BASE + extra, 2)


if __name__ == "__main__":
    main()
