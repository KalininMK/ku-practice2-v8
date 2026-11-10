"""Проверки нормализации штатного дерева только для сравнения."""

import unittest

from verification.native import graph_edges, native_graph


class NativeReferenceTests(unittest.TestCase):
    """Штатный служебный корень и dedup не должны искажать сравнение."""

    def test_wrapper_removed(self):
        """Сохранить выбранный корень без внешнего проекта npm."""
        data = {"name": "reference", "version": "1.0.0", "dependencies": {
            "app": {"version": "2.0.0", "dependencies": {
                "lib": {"version": "1.0.0"}}}}}
        result = native_graph(data, "app", "2.0.0")
        self.assertEqual(result, {("app", "2.0.0"): [("lib", "1.0.0")],
                                  ("lib", "1.0.0"): []})

    def test_dedup_preserves_known_edges(self):
        """Повтор версии не должен стирать ранее прочитанный подграф."""
        leaf = {"version": "1.0.0"}
        data = {"dependencies": {"app": {"version": "1.0.0", "dependencies": {
            "left": {"version": "1.0.0", "dependencies": {
                "shared": {"version": "1.0.0", "dependencies": {"end": leaf}}}},
            "right": {"version": "1.0.0", "dependencies": {
                "shared": {"version": "1.0.0", "deduped": True}}},
        }}}}
        result = native_graph(data, "app", "1.0.0")
        self.assertIn((("shared", "1.0.0"), ("end", "1.0.0")),
                      graph_edges(result))
        self.assertEqual(len(result), 5)

    def test_invalid_native_tree(self):
        """Потребовать выбранное имя и конкретную исходную версию."""
        examples = [[], {}, {"dependencies": []},
                    {"dependencies": {"app": {}}},
                    {"dependencies": {"app": {"version": "2.0.0"}}}]
        for document in examples:
            with self.subTest(document=document):
                with self.assertRaises(ValueError):
                    native_graph(document, "app", "1.0.0")
