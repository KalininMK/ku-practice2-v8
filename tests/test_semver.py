"""Проверки собственного выбора версий npm."""

import unittest

from src.semver import satisfies, select_version, version_key


class SemverTests(unittest.TestCase):
    """Граничные условия SemVer и распространённых диапазонов."""

    def assert_cases(self, requirement, accepted, rejected):
        """Проверить несколько значений относительно диапазона."""
        for version in accepted:
            with self.subTest(requirement=requirement, version=version):
                self.assertTrue(satisfies(version, requirement))
        for version in rejected:
            with self.subTest(requirement=requirement, version=version):
                self.assertFalse(satisfies(version, requirement))

    def test_numeric_order(self):
        """Сравнивать числа, не строки."""
        self.assertGreater(version_key("1.10.0"), version_key("1.9.9"))

    def test_prerelease_order(self):
        """Сравнить числовые идентификаторы и приоритет релиза."""
        versions = ["1.0.0-alpha.2", "1.0.0-alpha.10", "1.0.0-beta",
                    "1.0.0"]
        self.assertEqual(sorted(reversed(versions), key=version_key), versions)

    def test_build_metadata(self):
        """Метаданные сборки не меняют приоритет."""
        self.assertEqual(version_key("1.0.0+abc"), version_key("1.0.0+xyz"))

    def test_caret(self):
        """Caret ограничивает первую значимую часть версии."""
        self.assert_cases("^1.2.3", ["1.2.3", "1.9.0"], ["1.2.2", "2.0.0"])
        self.assert_cases("^0.2.3", ["0.2.9"], ["0.3.0"])
        self.assert_cases("^0.0.3", ["0.0.3"], ["0.0.4"])

    def test_partial_caret(self):
        """Учесть пропущенные нулевые части caret."""
        self.assert_cases("^0", ["0.9.0"], ["1.0.0"])
        self.assert_cases("^0.0", ["0.0.9"], ["0.1.0"])

    def test_tilde(self):
        """Tilde разрешает нужный уровень изменений."""
        self.assert_cases("~1.2.3", ["1.2.9"], ["1.3.0"])
        self.assert_cases("~1", ["1.9.0"], ["2.0.0"])

    def test_wildcards(self):
        """Поддержать wildcard и частичные версии."""
        self.assert_cases("1.2.x", ["1.2.0", "1.2.99"], ["1.3.0"])
        self.assert_cases("1", ["1.9.0"], ["2.0.0"])
        self.assert_cases("*", ["0.0.0", "9.0.0"], ["1.0.0-beta"])

    def test_comparators(self):
        """Поддержать AND и частичные сравнения."""
        self.assert_cases(">=1.2.3 <2", ["1.2.3", "1.9.0"], ["2.0.0"])
        self.assert_cases(">1.2", ["1.3.0"], ["1.2.99"])
        self.assert_cases("<=1.2", ["1.2.99"], ["1.3.0"])

    def test_alternatives_and_hyphen(self):
        """Поддержать OR и диапазон с дефисом."""
        self.assert_cases("1.x || 3.x", ["1.5.0", "3.0.0"], ["2.0.0"])
        self.assert_cases("1.2 - 2.3", ["1.2.0", "2.3.9"], ["2.4.0"])

    def test_prerelease_eligibility(self):
        """Допускать prerelease только для явно указанного ядра."""
        self.assert_cases("^1.2.3-beta.1", ["1.2.3-beta.2", "1.3.0"],
                          ["1.2.4-beta", "2.0.0-alpha"])
        self.assertFalse(satisfies("1.2.0-alpha", ">=1.2.0-alpha <1.2"))

    def test_maximum_selection(self):
        """Выбрать максимальную допустимую версию."""
        self.assertEqual(select_version(
            ["1.9.0", "2.0.0", "1.10.0", "invalid"], "^1.0.0"), "1.10.0")

    def test_unavailable_or_unsupported(self):
        """Не подменять несовместимое требование произвольной версией."""
        for requirement in ["^2.0.0", "git+https://example.org/a.git",
                            "npm:alias@1", "1.x.3"]:
            with self.subTest(requirement=requirement):
                with self.assertRaises(ValueError):
                    select_version(["1.0.0"], requirement)
