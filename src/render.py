"""Graphviz DOT, SVG и безопасное ASCII-представление графа."""

import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as element_tree

from .graph import node_label

RENDER_TIMEOUT = 60


def to_dot(graph):
    """Сформировать DOT с отдельными идентификаторами и подписями."""
    nodes = sorted(graph, key=node_label)
    identifiers = {node: f"n{index}" for index, node in enumerate(nodes)}
    lines = ["digraph dependencies {", "  rankdir=LR;", "  node [shape=box];"]
    for node in nodes:
        label = json.dumps(node_label(node), ensure_ascii=False)
        lines.append(f"  {identifiers[node]} [label={label}];")
    for node in nodes:
        for dependency in sorted(set(graph[node]), key=node_label):
            if dependency not in identifiers:
                raise ValueError("Граф содержит необъявленную вершину")
            lines.append(f"  {identifiers[node]} -> {identifiers[dependency]};")
    return "\n".join(lines + ["}", ""])


def validate_svg(data):
    """Проверить XML и корневой элемент SVG."""
    try:
        root = element_tree.fromstring(data)
    except element_tree.ParseError as error:
        raise ValueError("Graphviz вернул некорректный XML") from error
    if root.tag != "{http://www.w3.org/2000/svg}svg":
        raise ValueError("Graphviz не вернул SVG")


def render_svg(graph, output, dot="dot"):
    """Записать DOT и получить SVG через Graphviz, без shell."""
    output = Path(output)
    source = to_dot(graph)
    output.with_suffix(".dot").write_text(source, encoding="utf-8")
    try:
        process = subprocess.run(
            [dot, "-Tsvg"], input=source.encode("utf-8"),
            capture_output=True, timeout=RENDER_TIMEOUT,
        )
    except FileNotFoundError as error:
        message = "Graphviz не найден: установите dot или задайте --dot"
        raise ValueError(message) from error
    if process.returncode:
        message = process.stderr.decode("utf-8", errors="replace")
        raise ValueError(f"Ошибка Graphviz: {message}")
    validate_svg(process.stdout)
    output.write_bytes(process.stdout)
    return output


def to_ascii(graph, root):
    """Сформировать ASCII-дерево, помечая циклы и общие подграфы."""
    if root not in graph:
        raise ValueError("Начальный пакет отсутствует в графе")
    lines, expanded = [], set()

    def visit(node, prefix, connector, ancestors):
        """Развернуть готовый граф в строки без повторного обхода циклов."""
        marker = " [cycle]" if node in ancestors else ""
        if not marker and node in expanded:
            marker = " [shown]"
        lines.append(prefix + connector + node_label(node) + marker)
        if marker:
            return
        expanded.add(node)
        children = sorted(set(graph[node]), key=node_label)
        child_prefix = prefix
        if connector:
            child_prefix += "    " if connector == "\\-- " else "|   "
        for index, child in enumerate(children):
            last = index == len(children) - 1
            branch = "\\-- " if last else "+-- "
            visit(child, child_prefix, branch, ancestors | {node})

    try:
        visit(root, "", "", set())
    except RecursionError as error:
        raise ValueError("Превышена глубина отображения дерева") from error
    return "\n".join(lines)
