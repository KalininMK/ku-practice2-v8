"""Практическая работа 2, вариант 8. Этап 1: настройки CLI."""

import argparse
from pathlib import Path
import re
from urllib.parse import urlsplit


MAX_PACKAGE_LENGTH = 214
NPM_NAME = (
    r"(?:@[a-z0-9._~-]+/[a-z0-9._~-]+|"
    r"[a-z0-9~-][a-z0-9._~-]*)"
)
NUMBER = r"(?:0|[1-9][0-9]*)"
PRERELEASE = (
    rf"(?:{NUMBER}|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*)"
)
SEMVER = (
    rf"{NUMBER}\.{NUMBER}\.{NUMBER}"
    rf"(?:-{PRERELEASE}(?:\.{PRERELEASE})*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
)


def build_parser():
    """Описать семь параметров варианта 8."""
    parser = argparse.ArgumentParser(
        description="npm dependencies: вариант 8, этап 1",
        allow_abbrev=False,
    )
    parser.add_argument("--package", required=True, help="Имя пакета")
    parser.add_argument(
        "--repository", required=True, help="URL реестра или путь JSON"
    )
    parser.add_argument("--test", action="store_true", help="Тестовый режим")
    parser.add_argument("--version", required=True, help="Точная версия")
    parser.add_argument("--output", default="graph.svg", help="Путь SVG")
    parser.add_argument(
        "--ascii", dest="ascii_tree", action="store_true",
        help="Выводить ASCII-дерево",
    )
    parser.add_argument("--filter", default="", help="Подстрока исключения")
    return parser


def validate_package(args):
    """Проверить структуру имени npm или тестового пакета."""
    pattern = r"[A-Z]+" if args.test else NPM_NAME
    if not re.fullmatch(pattern, args.package):
        raise ValueError("--package: недопустимое имя пакета")
    if len(args.package) > MAX_PACKAGE_LENGTH:
        raise ValueError("--package: имя длиннее 214 символов")


def validate_url_details(url):
    """Отклонить лишние части URL и неверный порт."""
    if any((url.username, url.password, url.query, url.fragment)):
        raise ValueError("--repository: лишние части URL реестра")
    try:
        url.port
    except ValueError as error:
        raise ValueError("--repository: неверный порт") from error


def validate_registry_url(address):
    """Проверить HTTP(S)-адрес реестра."""
    url = urlsplit(address)
    if url.scheme not in {"http", "https"} or not url.hostname:
        raise ValueError("--repository: нужен полный HTTP(S) URL")
    if any(char.isspace() for char in address):
        raise ValueError("--repository: пробелы в URL недопустимы")
    validate_url_details(url)


def validate_repository(args):
    """Проверить локальный файл или адрес реестра."""
    if args.test:
        if not Path(args.repository).is_file():
            raise ValueError("--repository: тестовый файл не найден")
        return
    validate_registry_url(args.repository)

def validate_version(args):
    """Потребовать точную версию SemVer, а не диапазон или latest."""
    if not re.fullmatch(SEMVER, args.version):
        raise ValueError("--version: нужна точная версия, например 3.0.1")


def validate_output(args):
    """Проверить расширение SVG и родительскую папку."""
    output = Path(args.output)
    if output.suffix.lower() != ".svg" or output.is_dir():
        raise ValueError("--output: нужен путь к файлу .svg")
    if not output.parent.is_dir():
        raise ValueError("--output: родительская папка не существует")


def validate_filter(args):
    """Проверить подстроку и исключение начального пакета."""
    if args.filter and (
        not args.filter.strip() or not args.filter.isprintable()
    ):
        raise ValueError("--filter: недопустимая подстрока")
    if args.filter and args.filter in args.package:
        raise ValueError("--filter: исключает начальный пакет")


def arguments(argv=None):
    """Прочитать параметры и объяснить ошибки пользователю."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        validate_package(args)
        validate_repository(args)
        validate_version(args)
        validate_output(args)
        validate_filter(args)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    return args


def main(argv=None):
    """На первом этапе вывести все настройки ключ=значение."""
    args = arguments(argv)
    for key, value in vars(args).items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
