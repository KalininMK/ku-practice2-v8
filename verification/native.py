"""Нормализация результата npm ls только для контрольного сравнения."""

from src.graph import node_label


def read_node(name, record, graph):
    """Добавить узел штатного дерева и все его явно указанные связи."""
    if (not isinstance(record, dict)
            or not isinstance(record.get("version"), str)):
        raise ValueError("В выводе npm отсутствует конкретная версия")
    node = name, record["version"]
    edges = graph.setdefault(node, set())
    children = record.get("dependencies", {})
    if not isinstance(children, dict):
        raise ValueError("Некорректное дерево npm ls")
    for child_name, child in children.items():
        edges.add(read_node(child_name, child, graph))
    return node


def native_graph(document, name, version):
    """Убрать служебный корень проекта, сохранив пакеты и версии."""
    if not isinstance(document, dict):
        raise ValueError("Некорректный JSON npm ls")
    dependencies = document.get("dependencies", {})
    if not isinstance(dependencies, dict) or name not in dependencies:
        raise ValueError("Запрошенный пакет не найден в дереве npm")
    graph = {}
    root = read_node(name, dependencies[name], graph)
    if root != (name, version):
        raise ValueError("npm установил другую версию начального пакета")
    return {node: sorted(edges, key=node_label)
            for node, edges in graph.items()}


def graph_edges(graph):
    """Получить множество пар с конкретными версиями пакетов."""
    return {(source, target) for source, targets in graph.items()
            for target in targets}
