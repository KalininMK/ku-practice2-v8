"""Практическая работа 2, вариант 8. Этап 4: обратные зависимости npm."""

import argparse
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

from .graph import (
    bfs, load_test_graph, node_label, print_graph, reverse_graph,
)
from .npm_graph import MAX_PACKAGE_LENGTH, NPM_NAME, NpmRepository
from .reverse import read_roots, universe_graph
from .semver import SEMVER


def build_parser():
    """Описать базовые настройки и режимы графа."""
    parser = argparse.ArgumentParser(
        description="npm dependencies: вариант 8, этап 4",
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
    parser.add_argument(
        "--reverse", action="store_true", help="Обратные зависимости"
    )
    parser.add_argument(
        "--roots", help="JSON исходных npm-пакетов для обратного анализа"
    )
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


def validate_reverse_options(args):
    """Проверить область обратного анализа настоящего реестра."""
    if args.roots and not args.reverse:
        raise ValueError("--roots используется вместе с --reverse")
    if args.test and args.roots:
        raise ValueError("--roots нужен только для настоящего реестра npm")
    if args.reverse and not args.test and not args.roots:
        raise ValueError("Для npm --reverse укажите область поиска --roots")
    if args.roots and not Path(args.roots).is_file():
        raise ValueError("--roots: файл не найден")


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
        validate_reverse_options(args)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    return args


def root_node(args):
    """Получить идентификатор начального пакета."""
    return args.package if args.test else (args.package, args.version)


def selected_graph(args):
    """Построить прямой или обратный граф тем же рекурсивным BFS."""
    root = root_node(args)
    if args.test:
        graph = load_test_graph(args.repository)
    else:
        repository = NpmRepository(args.repository, args.filter)
        if not args.reverse:
            return bfs(repository.dependencies, root, args.filter)
        graph = universe_graph(repository, root,
                               read_roots(args.roots), args.filter)
    if args.reverse:
        graph = reverse_graph(graph)
    return bfs(graph, root, args.filter)


def main(argv=None):
    """Вывести граф и список непосредственных и косвенных зависимых."""
    args = arguments(argv)
    try:
        graph = selected_graph(args)
        print_graph(graph)
        if args.reverse:
            names = [node_label(node) for node in graph
                     if node != root_node(args)]
            print("Обратные зависимости: " + (", ".join(names) or "(нет)"))
    except (OSError, ValueError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
