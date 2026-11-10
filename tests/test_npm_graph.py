"""Проверки npm-графа без сети и менеджеров пакетов."""

import unittest
from unittest.mock import patch

from src.graph import bfs
from src.npm_graph import NpmRepository


def catalog(name, versions, tags=None):
    """Создать тестовый каталог версий и зависимостей."""
    return {"name": name, "dist-tags": tags or {}, "versions": {
        version: {"name": name, "version": version, "dependencies": deps}
        for version, deps in versions.items()
    }}


class NpmGraphTests(unittest.TestCase):
    """Выбор версий, кэширование и обход реальных имён."""

    def setUp(self):
        """Подготовить каталоги с несколькими подходящими версиями."""
        self.data = {
            "app": catalog("app", {"1.0.0": {"lib": "^1.0.0"}}),
            "lib": catalog("lib", {"1.0.0": {}, "1.9.0": {}, "2.0.0": {}}),
        }
        self.repository = NpmRepository("https://example.org")

    def test_version_resolution(self):
        """Выбрать максимальную совместимую версию зависимости."""
        with patch("src.npm_graph.fetch_catalog",
                   side_effect=lambda name, url: self.data[name]):
            graph = bfs(self.repository.dependencies, ("app", "1.0.0"))
        self.assertEqual(graph, {("app", "1.0.0"): [("lib", "1.9.0")],
                                 ("lib", "1.9.0"): []})

    def test_cache(self):
        """Повторные требования не должны повторять HTTP-запросы."""
        with patch("src.npm_graph.fetch_catalog",
                   side_effect=lambda name, url: self.data[name]) as fetch:
            self.repository.resolve("lib", "^1.0.0")
            self.repository.resolve("lib", "^1.0.0")
            self.repository.resolve("lib", "~1.0.0")
        self.assertEqual(fetch.call_count, 1)

    def test_cycle(self):
        """Рекурсивный BFS должен завершаться при npm-цикле."""
        self.data["lib"] = catalog("lib", {"1.0.0": {"app": "1.0.0"}})
        with patch("src.npm_graph.fetch_catalog",
                   side_effect=lambda name, url: self.data[name]):
            graph = bfs(self.repository.dependencies, ("app", "1.0.0"))
        self.assertEqual(len(graph), 2)
        self.assertEqual(graph[("lib", "1.0.0")], [("app", "1.0.0")])

    def test_filter_before_download(self):
        """Не скачивать каталог исключённого пакета."""
        repository = NpmRepository("https://example.org", "lib")
        with patch("src.npm_graph.fetch_catalog",
                   side_effect=lambda name, url: self.data[name]) as fetch:
            graph = bfs(repository.dependencies, ("app", "1.0.0"), "lib")
        self.assertEqual(graph, {("app", "1.0.0"): []})
        self.assertEqual(fetch.call_count, 1)

    def test_dist_tag(self):
        """Разрешить dist-tag в требовании зависимости."""
        self.data["lib"]["dist-tags"] = {"latest": "1.9.0"}
        with patch("src.npm_graph.fetch_catalog",
                   return_value=self.data["lib"]):
            self.assertEqual(self.repository.resolve("lib", "latest"),
                             ("lib", "1.9.0"))

    def test_root_version_missing(self):
        """Точную версию корня не заменять другой существующей."""
        with patch("src.npm_graph.fetch_catalog",
                   return_value=self.data["app"]):
            with self.assertRaisesRegex(ValueError, "не найден"):
                self.repository.dependencies(("app", "9.0.0"))

    def test_invalid_catalog(self):
        """Проверить структуру и имя каталога."""
        for value in [[], {}, {"name": "lib", "versions": []}]:
            with self.subTest(value=value):
                repository = NpmRepository("https://example.org")
                with patch("src.npm_graph.fetch_catalog", return_value=value):
                    with self.assertRaises(ValueError):
                        repository.catalog("lib")

    def test_incompatible_requirement(self):
        """Сообщить об отсутствии совместимой версии."""
        with patch("src.npm_graph.fetch_catalog",
                   return_value=self.data["lib"]):
            with self.assertRaises(ValueError):
                self.repository.resolve("lib", "^3.0.0")
