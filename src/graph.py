"""Тестовый репозиторий и рекурсивный обход по уровням BFS."""

import json
from pathlib import Path
import re


def node_name(node):
    """Получить имя без версии для фильтрации."""
    return node[0] if isinstance(node, tuple) else node


def node_label(node):
    """Получить подпись пакета, включая конкретную версию npm."""
    return f"{node[0]}@{node[1]}" if isinstance(node, tuple) else node


def load_test_graph(path):
    """Прочитать JSON с именами A-Z и проверить ссылки."""
    graph = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(graph, dict) or not graph:
        raise ValueError("Нужен непустой JSON-объект графа")
    for name, dependencies in graph.items():
        if not re.fullmatch(r"[A-Z]+", name):
            raise ValueError("Имена тестовых пакетов: только A-Z")
        if not isinstance(dependencies, list):
            raise ValueError(f"{name}: зависимости должны быть списком")
        for dependency in dependencies:
            if not isinstance(dependency, str) or dependency not in graph:
                raise ValueError(f"{name}: неизвестная зависимость")
    return graph


def bfs(graph, start, excluded=""):
    """Обойти граф BFS с рекурсией между целыми уровнями."""
    if not callable(graph) and start not in graph:
        raise ValueError(f"Пакет {node_label(start)} не найден")
    if excluded and excluded in node_name(start):
        raise ValueError("Фильтр исключает начальный пакет")
    neighbors = graph if callable(graph) else graph.__getitem__
    visited = {start}
    result = {}

    def visit_level(frontier):
        """Обработать текущий уровень и рекурсивно перейти к следующему."""
        next_level = []
        for node in frontier:
            edges = sorted(set(neighbors(node)), key=node_label)
            edges = [dep for dep in edges
                     if not excluded or excluded not in node_name(dep)]
            result[node] = edges
            for dependency in edges:
                if dependency not in visited:
                    visited.add(dependency)
                    next_level.append(dependency)
        if next_level:
            visit_level(next_level)

    try:
        visit_level([start])
    except RecursionError as error:
        raise ValueError("Превышена глубина рекурсии BFS") from error
    return result


def print_graph(graph):
    """Показать вершины в порядке BFS и их зависимости."""
    for node, dependencies in graph.items():
        text = ", ".join(map(node_label, dependencies)) or "(нет)"
        print(node_label(node) + " -> " + text)



def reverse_graph(graph):
    """Развернуть все рёбра полного переданного графа."""
    result = {node: [] for node in graph}
    for node, dependencies in graph.items():
        for dependency in dependencies:
            result[dependency].append(node)
    return {node: sorted(set(dependencies), key=node_label)
            for node, dependencies in result.items()}
