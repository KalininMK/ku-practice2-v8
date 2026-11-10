"""Явная область обратного анализа пакетов npm."""

import json
from pathlib import Path
import re

from .graph import bfs, node_name
from .npm_graph import MAX_PACKAGE_LENGTH, NPM_NAME
from .semver import SEMVER


def validate_root(record):
    """Прочитать имя и точную версию исходного пакета."""
    if not isinstance(record, dict):
        raise ValueError("Элемент --roots должен быть JSON-объектом")
    name, version = record.get("package"), record.get("version")
    if not isinstance(name, str) or not re.fullmatch(NPM_NAME, name):
        raise ValueError("Некорректное имя пакета в --roots")
    if len(name) > MAX_PACKAGE_LENGTH:
        raise ValueError("Слишком длинное имя пакета в --roots")
    if not isinstance(version, str) or not re.fullmatch(SEMVER, version):
        raise ValueError("В --roots нужна точная версия SemVer")
    return name, version


def read_roots(path):
    """Прочитать непустой список исходных пакетов без повторов."""
    value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(value, list) or not value:
        raise ValueError("--roots должен содержать непустой JSON-список")
    return list(dict.fromkeys(validate_root(record) for record in value))


def universe_graph(repository, target, roots, excluded=""):
    """Объединить транзитивные графы запроса и заданных корней."""
    graph = {}
    for root in [target] + roots:
        if excluded and excluded in node_name(root):
            continue
        if root not in graph:
            graph.update(bfs(repository.dependencies, root, excluded))
    return graph
