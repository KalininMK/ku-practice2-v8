"""Демонстрация CLI второго этапа на тестовом HTTP-ответе."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import shlex
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.main import main as program

BASE = ["--package", "is-odd", "--repository",
        "https://registry.npmjs.org", "--version", "3.0.1"]


def fake_response(request, timeout):
    """Подменить HTTP для демонстрации без обращения к сети."""
    metadata = {"name": "is-odd", "version": "3.0.1",
                "dependencies": {"is-number": "^6.0.0"}}
    return io.BytesIO(json.dumps(metadata).encode("utf-8"))


def run(argv, expected):
    """Показать результат запуска и проверить код возврата."""
    output, errors = io.StringIO(), io.StringIO()
    print("$ python -m src.main " + shlex.join(argv))
    with patch("src.registry.urlopen", side_effect=fake_response):
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
    """Показать пример вывода и ошибки семи параметров."""
    print("Офлайн-демонстрация: HTTP-ответ явно подменён тестовым.")
    run(BASE, 0)
    cases = [["--package", "bad name"], ["--repository", "bad"],
             ["--test", "yes"], ["--version", "latest"],
             ["--output", "graph.png"], ["--ascii", "yes"],
             ["--filter", "   "]]
    for extra in cases:
        run(BASE + extra, 2)


if __name__ == "__main__":
    main()
