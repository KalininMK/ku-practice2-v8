"""Проверки рекурсивного BFS и локального JSON-графа."""

import json
from pathlib import Path
import tempfile
import unittest

from src.graph import bfs, load_test_graph, node_label, node_name

DIAMOND = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}


class GraphTests(unittest.TestCase):
    """Обход должен оставаться в ширину при наличии рекурсии."""

    def test_bfs_order(self):
        """Обработать весь уровень до перехода к следующему."""
        graph = {"A": ["C", "B"], "B": ["D"], "C": [], "D": []}
        self.assertEqual(list(bfs(graph, "A")), ["A", "B", "C", "D"])

    def test_cycle(self):
        """Сохранить рёбра цикла и закончить обход."""
        graph = {"A": ["B"], "B": ["C"], "C": ["A"]}
        self.assertEqual(bfs(graph, "A"), graph)

    def test_self_cycle(self):
        """Обработать петлю в одной вершине."""
        self.assertEqual(bfs({"A": ["A"]}, "A"), {"A": ["A"]})

    def test_shared_dependency(self):
        """Сохранить обе связи с одной общей зависимостью."""
        self.assertEqual(bfs(DIAMOND, "A"), DIAMOND)

    def test_chain_filter(self):
        """Фильтр отсекает путь через исключённую вершину."""
        graph = {"A": ["B"], "B": ["C"], "C": []}
        self.assertEqual(bfs(graph, "A", "B"), {"A": []})

    def test_diamond_filter(self):
        """Общая вершина остаётся при наличии другого пути."""
        self.assertEqual(bfs(DIAMOND, "A", "B"),
                         {"A": ["C"], "C": ["D"], "D": []})

    def test_isolated(self):
        """Обойти единственную вершину без зависимостей."""
        self.assertEqual(bfs({"A": []}, "A"), {"A": []})

    def test_bad_root(self):
        """Отклонить отсутствующий или исключённый корень."""
        for name, excluded in [("Z", ""), ("A", "A")]:
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    bfs(DIAMOND, name, excluded)

    def test_wide_level(self):
        """Ширина уровня не должна увеличивать глубину рекурсии."""
        graph = {"ROOT": [f"N{number}" for number in range(2000)]}
        graph.update({name: [] for name in graph["ROOT"]})
        self.assertEqual(len(bfs(graph, "ROOT")), len(graph))

    def test_callable_and_versions(self):
        """Фильтровать имя, а не строку с номером версии."""
        root, child = ("app", "6.0.0"), ("lib", "6.0.0")
        graph = {root: [child], child: []}
        self.assertEqual(bfs(graph.__getitem__, root, "6"), graph)
        self.assertEqual(node_label(root), "app@6.0.0")
        self.assertEqual(node_name(child), "lib")

    def test_read_json(self):
        """Прочитать граф, включая UTF-8 BOM."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "graph.json"
            path.write_text(json.dumps(DIAMOND), encoding="utf-8-sig")
            self.assertEqual(load_test_graph(path), DIAMOND)

    def test_invalid_json(self):
        """Отклонить неверный формат и несуществующие зависимости."""
        cases = [[], {}, {"a": []}, {"A": "B"}, {"A": ["B"]}, {"A": [1]}]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "graph.json"
            for graph in cases:
                path.write_text(json.dumps(graph), encoding="utf-8")
                with self.subTest(graph=graph):
                    with self.assertRaises(ValueError):
                        load_test_graph(path)
            path.write_text("{", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_test_graph(path)
