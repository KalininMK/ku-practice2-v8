"""Демонстрация настроек и ошибок всех семи параметров."""

from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = ["--package", "is-odd", "--repository",
        "https://registry.npmjs.org", "--version", "3.0.1"]


def run(argv, expected):
    """Показать команду, вывод и проверить код завершения."""
    command = [sys.executable, "-m", "src.main"] + argv
    print("$ " + shlex.join(command), flush=True)
    result = subprocess.run(command, cwd=ROOT, capture_output=True,
                            text=True, encoding="utf-8")
    print(result.stdout, end="")
    print(result.stderr, end="")
    print(f"Код завершения: {result.returncode}\n", flush=True)
    if result.returncode != expected:
        raise SystemExit("Неожиданный код завершения")


def main():
    """Показать успешные запуски и семь ошибочных случаев."""
    run(BASE, 0)
    run(["--package", "A", "--repository", "tests/fixtures/chain.json",
         "--version", "1.0.0", "--test", "--ascii", "--filter", "Z"], 0)
    cases = [
        ["--package", "bad name"], ["--repository", "not-a-url"],
        ["--test", "yes"], ["--version", "latest"],
        ["--output", "graph.png"], ["--ascii", "yes"],
        ["--filter", "   "],
    ]
    for extra in cases:
        run(BASE + extra, 2)


if __name__ == "__main__":
    main()
