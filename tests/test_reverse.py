"""Проверки обратных зависимостей и явно заданной npm-области."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.graph import bfs, reverse_graph
from src.main import arguments, main
from src.npm_graph import NpmRepository
from src.reverse import read_roots, universe_graph

CHAIN = {"A": ["B"], "B": ["C"], "C": []}
DIAMOND = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}


def catalog(name, version, dependencies):
    """Создать небольшой каталог одной версии npm."""
    return {"name": name, "versions": {version: {
        "name": name, "version": version, "dependencies": dependencies,
    }}}


class ReverseTests(unittest.TestCase):
    """Разворот всего графа и повторное использование BFS."""

    def json_run(self, root, fixture="chain", excluded=""):
        """Запустить CLI обратного анализа тестового файла."""
        output, errors = io.StringIO(), io.StringIO()
        argv = ["--package", root, "--version", "1.0.0", "--test",
                "--repository", f"tests/fixtures/{fixture}.json",
                "--reverse", "--filter", excluded]
        with redirect_stdout(output), redirect_stderr(errors):
            code = main(argv)
        return code, output.getvalue(), errors.getvalue()

    def test_reverse_edges(self):
        """Сохранить все вершины, включая изолированную."""
        graph = dict(CHAIN, D=[])
        self.assertEqual(reverse_graph(graph),
                         {"A": [], "B": ["A"], "C": ["B"], "D": []})

    def test_transitive(self):
        """Найти непосредственных и косвенных зависимых."""
        result = bfs(reverse_graph(CHAIN), "C")
        self.assertEqual(result, {"C": ["B"], "B": ["A"], "A": []})
        self.assertEqual(list(result), ["C", "B", "A"])

    def test_branching(self):
        """Сохранить общую обратную зависимость и порядок BFS."""
        result = bfs(reverse_graph(DIAMOND), "D")
        self.assertEqual(list(result), ["D", "B", "C", "A"])
        self.assertEqual(result["B"], ["A"])
        self.assertEqual(result["C"], ["A"])

    def test_cycle(self):
        """Завершить обратный обход цикла, сохранив рёбра."""
        graph = {"A": ["B"], "B": ["C"], "C": ["A"]}
        self.assertEqual(bfs(reverse_graph(graph), "A"),
                         {"A": ["C"], "C": ["B"], "B": ["A"]})

    def test_self_cycle(self):
        """Обработать петлю при обратном обходе."""
        graph = {"A": ["A"]}
        self.assertEqual(bfs(reverse_graph(graph), "A"), graph)

    def test_filter_chain(self):
        """Исключение B отсекает и путь к A."""
        self.assertEqual(bfs(reverse_graph(CHAIN), "C", "B"), {"C": []})

    def test_filter_diamond(self):
        """Общая вершина остаётся через другую обратную ветвь."""
        self.assertEqual(bfs(reverse_graph(DIAMOND), "D", "B"),
                         {"D": ["C"], "C": ["A"], "A": []})

    def test_no_dependents(self):
        """Обратные зависимости могут отсутствовать."""
        self.assertEqual(bfs(reverse_graph(CHAIN), "A"), {"A": []})

    def test_json_cli(self):
        """Не включать корень в итоговый список зависимых."""
        code, text, errors = self.json_run("C")
        self.assertEqual(code, 0)
        self.assertEqual(errors, "")
        self.assertEqual(text, "C -> B\nB -> A\nA -> (нет)\n"
                         "Обратные зависимости: B, A\n")

    def test_unknown_json_root(self):
        """Объяснить отсутствие корня в тестовом репозитории."""
        code, _, errors = self.json_run("Z")
        self.assertEqual(code, 1)
        self.assertIn("не найден", errors)

    def test_roots_file(self):
        """Прочитать конкретные версии и убрать повторы."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "roots.json"
            records = [{"package": "parent", "version": "1.0.0"}] * 2
            path.write_text(json.dumps(records), encoding="utf-8-sig")
            self.assertEqual(read_roots(path), [("parent", "1.0.0")])

    def test_invalid_roots(self):
        """Отклонить некорректные исходные пакеты."""
        cases = [[], {}, ["lib"], [{"package": "lib"}],
                 [{"package": "UPPER", "version": "1.0.0"}],
                 [{"package": "lib", "version": "^1.0.0"}]]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "roots.json"
            for records in cases:
                path.write_text(json.dumps(records), encoding="utf-8")
                with self.subTest(records=records):
                    with self.assertRaises(ValueError):
                        read_roots(path)

    def test_npm_scope_cli(self):
        """Найти пакет вне прямого графа запрошенной библиотеки."""
        data = {
            "library": catalog("library", "1.0.0", {}),
            "parent": catalog("parent", "2.0.0", {"library": "^1.0.0"}),
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "roots.json"
            path.write_text(json.dumps([
                {"package": "parent", "version": "2.0.0"}
            ]), encoding="utf-8")
            output = io.StringIO()
            with patch("src.npm_graph.fetch_catalog",
                       side_effect=lambda name, url: data[name]) as fetch:
                with redirect_stdout(output):
                    code = main([
                        "--package", "library", "--version", "1.0.0",
                        "--repository", "https://example.org",
                        "--reverse", "--roots", str(path),
                    ])
        self.assertEqual(code, 0)
        self.assertEqual(fetch.call_count, 2)
        self.assertEqual(output.getvalue(),
                         "library@1.0.0 -> parent@2.0.0\n"
                         "parent@2.0.0 -> (нет)\n"
                         "Обратные зависимости: parent@2.0.0\n")

    def test_reverse_options(self):
        """Потребовать явную область для настоящего npm."""
        base = ["--package", "lib", "--version", "1.0.0",
                "--repository", "https://example.org"]
        cases = [["--reverse"], ["--roots", "missing.json"],
                 ["--reverse", "--roots", "missing.json"]]
        for extra in cases:
            with self.subTest(extra=extra), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    arguments(base + extra)
                self.assertEqual(caught.exception.code, 2)

    def test_filtered_seed(self):
        """Не загружать исключённый исходный пакет."""
        repository = NpmRepository("https://example.org", "parent")
        with patch("src.npm_graph.fetch_catalog",
                   return_value=catalog("library", "1.0.0", {})) as fetch:
            graph = universe_graph(repository, ("library", "1.0.0"),
                                   [("parent", "2.0.0")], "parent")
        self.assertEqual(graph, {("library", "1.0.0"): []})
        self.assertEqual(fetch.call_count, 1)
