"""Проверки Graphviz, ASCII-дерева и подключения к CLI."""

from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from src.main import main
from src.render import render_svg, to_ascii, to_dot

SVG = b'<svg xmlns="http://www.w3.org/2000/svg"></svg>'


def cli_arguments(directory):
    """Создать локальную цепочку и параметры визуализации."""
    path = Path(directory) / "graph.json"
    path.write_text('{"A": ["B"], "B": []}', encoding="utf-8")
    return ["--package", "A", "--version", "1.0.0", "--test",
            "--repository", str(path), "--visualize", "--output",
            str(Path(directory) / "graph.svg")]


class RenderTests(unittest.TestCase):
    """Внешний Graphviz в модульных тестах не запускается."""

    def test_dot_source(self):
        """Создать вершины, ребро и изолированный узел."""
        text = to_dot({"A": ["B"], "B": [], "C": []})
        self.assertTrue(text.startswith("digraph dependencies {"))
        self.assertIn('n0 [label="A"];', text)
        self.assertIn('n2 [label="C"];', text)
        self.assertIn("n0 -> n1;", text)
        self.assertTrue(text.endswith("}\n"))

    def test_dot_cycles(self):
        """Сохранить петлю и связи циклического графа."""
        text = to_dot({"A": ["A", "B"], "B": ["A"]})
        for edge in ["n0 -> n0;", "n0 -> n1;", "n1 -> n0;"]:
            self.assertIn(edge, text)

    def test_dot_escape(self):
        """Экранировать кавычки и обратный слеш в подписи."""
        text = to_dot({'a"b\\c': []})
        self.assertIn('label="a\\"b\\\\c"', text)

    def test_dot_unclosed_graph(self):
        """Не скрывать отсутствующие вершины в исходном графе."""
        with self.assertRaises(ValueError):
            to_dot({"A": ["missing"]})

    def test_svg_success(self):
        """Сохранить DOT и SVG после успешной отрисовки."""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "graph.svg"
            response = subprocess.CompletedProcess([], 0, SVG, b"")
            with patch("src.render.subprocess.run",
                       return_value=response) as run:
                result = render_svg({"A": []}, output, "path with spaces/dot")
            self.assertEqual(result, output)
            self.assertEqual(output.read_bytes(), SVG)
            self.assertIn('label="A"', output.with_suffix(".dot").read_text())
            self.assertEqual(run.call_args.args[0],
                             ["path with spaces/dot", "-Tsvg"])

    def test_graphviz_failure(self):
        """Сообщить об ошибке Graphviz и не создавать ложный SVG."""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "graph.svg"
            response = subprocess.CompletedProcess([], 1, b"", b"failed")
            with patch("src.render.subprocess.run", return_value=response):
                with self.assertRaisesRegex(ValueError, "failed"):
                    render_svg({"A": []}, output)
            self.assertFalse(output.exists())

    def test_invalid_svg(self):
        """Отклонить некорректный XML или другой тип документа."""
        for data in [b"not XML", b"<html/>"]:
            with self.subTest(data=data):
                with tempfile.TemporaryDirectory() as directory:
                    response = subprocess.CompletedProcess([], 0, data, b"")
                    with patch("src.render.subprocess.run",
                               return_value=response):
                        with self.assertRaises(ValueError):
                            render_svg({"A": []}, Path(directory) / "x.svg")

    def test_missing_dot(self):
        """Объяснить отсутствие исполняемого файла Graphviz."""
        with tempfile.TemporaryDirectory() as directory:
            with patch("src.render.subprocess.run",
                       side_effect=FileNotFoundError("dot")):
                with self.assertRaisesRegex(ValueError, "Graphviz не найден"):
                    render_svg({"A": []}, Path(directory) / "x.svg")

    def test_timeout(self):
        """Ограничить время ожидания внешней программы."""
        with tempfile.TemporaryDirectory() as directory:
            with patch("src.render.subprocess.run",
                       side_effect=subprocess.TimeoutExpired("dot", 60)):
                with self.assertRaises(subprocess.TimeoutExpired):
                    render_svg({"A": []}, Path(directory) / "x.svg")

    def test_ascii_branching(self):
        """Сохранить ASCII-разделители ветвей и порядок имён."""
        text = to_ascii({"A": ["C", "B"], "B": [], "C": []}, "A")
        self.assertEqual(text, "A\n+-- B\n\\-- C")
        self.assertTrue(text.isascii())

    def test_ascii_cycles(self):
        """Пометить циклы и остановить разворачивание."""
        text = to_ascii({"A": ["B"], "B": ["A"]}, "A")
        self.assertEqual(text, "A\n\\-- B\n    \\-- A [cycle]")
        self.assertEqual(to_ascii({"A": ["A"]}, "A"),
                         "A\n\\-- A [cycle]")

    def test_ascii_shared_node(self):
        """Повтор общего подграфа должен иметь пометку shown."""
        graph = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
        self.assertEqual(to_ascii(graph, "A"),
                         "A\n+-- B\n|   \\-- D\n\\-- C\n"
                         "    \\-- D [shown]")

    def test_ascii_isolated(self):
        """Показать одиночный пакет без лишних ветвей."""
        self.assertEqual(to_ascii({"A": []}, "A"), "A")

    def test_ascii_missing_root(self):
        """Сообщить об отсутствующем корне дерева."""
        with self.assertRaises(ValueError):
            to_ascii({"A": []}, "Z")

    def test_cli_visualization(self):
        """Передать выбранный граф и выходной путь отрисовке."""
        with tempfile.TemporaryDirectory() as directory:
            args = cli_arguments(directory)
            output = Path(directory) / "graph.svg"
            with patch("src.main.render_svg", return_value=output) as render:
                with redirect_stdout(io.StringIO()):
                    code = main(args)
            self.assertEqual(code, 0)
            render.assert_called_once_with({"A": ["B"], "B": []},
                                           str(output), "dot")

    def test_cli_render_error(self):
        """Ошибка внешнего процесса должна вернуть код 1."""
        with tempfile.TemporaryDirectory() as directory:
            args = cli_arguments(directory)
            errors = io.StringIO()
            with patch("src.main.render_svg",
                       side_effect=subprocess.TimeoutExpired("dot", 60)):
                with redirect_stdout(io.StringIO()), redirect_stderr(errors):
                    code = main(args)
            self.assertEqual(code, 1)
            self.assertIn("Ошибка:", errors.getvalue())

    def test_cli_ascii(self):
        """Переключить обычный текстовый вывод на ASCII-дерево."""
        with tempfile.TemporaryDirectory() as directory:
            args = cli_arguments(directory)
            args.remove("--visualize")
            output = io.StringIO()
            with redirect_stdout(output):
                code = main(args + ["--ascii"])
            self.assertEqual(code, 0)
            self.assertEqual(output.getvalue(), "A\n\\-- B\n")
