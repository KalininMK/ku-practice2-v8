"""Проверки семи параметров первого этапа."""

from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest

from src.main import arguments


class CliTests(unittest.TestCase):
    """Проверки настроек, ошибок и вывода CLI."""

    def base(self):
        """Вернуть правильные обязательные параметры."""
        return [
            "--package", "is-odd",
            "--repository", "https://registry.npmjs.org",
            "--version", "3.0.1",
        ]

    def rejected(self, argv):
        """Проверить ошибку CLI с кодом 2 и сообщением."""
        output = io.StringIO()
        with redirect_stderr(output):
            with self.assertRaises(SystemExit) as caught:
                arguments(argv)
        self.assertEqual(caught.exception.code, 2)
        self.assertIn("error:", output.getvalue())

    def test_defaults(self):
        """Проверить значения всех настроек по умолчанию."""
        args = arguments(self.base())
        self.assertEqual(args.package, "is-odd")
        self.assertEqual(args.repository, "https://registry.npmjs.org")
        self.assertEqual(args.version, "3.0.1")
        self.assertEqual(args.output, "graph.svg")
        self.assertFalse(args.test)
        self.assertFalse(args.ascii_tree)
        self.assertEqual(args.filter, "")

    def test_help(self):
        """Справка должна содержать все семь параметров."""
        output = io.StringIO()
        with redirect_stdout(output):
            with self.assertRaises(SystemExit) as caught:
                arguments(["--help"])
        self.assertEqual(caught.exception.code, 0)
        for flag in ["--package", "--repository", "--test", "--version",
                     "--output", "--ascii", "--filter"]:
            self.assertIn(flag, output.getvalue())

    def test_scoped_package(self):
        """Принять имя с областью npm."""
        args = arguments(self.base() + ["--package", "@scope/package"])
        self.assertEqual(args.package, "@scope/package")

    def test_bad_package(self):
        """Отклонить неправильную структуру и слишком длинное имя."""
        for name in ["bad name", "UPPER", ".hidden", "@scope", "a" * 215]:
            with self.subTest(name=name):
                self.rejected(self.base() + ["--package", name])

    def test_valid_versions(self):
        """Принять релиз, prerelease и метаданные сборки."""
        for version in ["0.0.0", "3.0.1", "1.0.0-beta.1", "1.0.0+001"]:
            with self.subTest(version=version):
                args = arguments(self.base() + ["--version", version])
                self.assertEqual(args.version, version)

    def test_bad_versions(self):
        """Отклонить диапазоны, псевдонимы и неверный SemVer."""
        for version in ["latest", "^3.0.0", "1.0", "01.0.0", "1.0.0-01"]:
            with self.subTest(version=version):
                self.rejected(self.base() + ["--version", version])

    def test_bad_registry(self):
        """Отклонить неподходящие адреса реестра."""
        examples = ["bad", "ftp://example.org", "https://",
                    "https://example.org:wrong", "https://bad host",
                    "https://example.org?q=1", "https://u:p@example.org"]
        for address in examples:
            with self.subTest(address=address):
                self.rejected(self.base() + ["--repository", address])

    def test_valid_test_mode(self):
        """Принять существующий тестовый файл и имя A-Z."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "graph.json"
            path.write_text('{"A": []}', encoding="utf-8")
            args = arguments(self.base() + [
                "--package", "A", "--repository", str(path), "--test",
            ])
            self.assertTrue(args.test)

    def test_missing_test_file(self):
        """Отклонить отсутствующий тестовый файл."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.json"
            self.rejected(self.base() + [
                "--package", "A", "--repository", str(path), "--test",
            ])

    def test_lowercase_test_name(self):
        """В тестовом режиме нужны большие латинские буквы."""
        self.rejected(self.base() + [
            "--repository", "tests/fixtures/chain.json", "--test",
        ])

    def test_bad_output(self):
        """Отклонить расширение, каталог и отсутствующую папку."""
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / "directory.svg"
            folder.mkdir()
            examples = ["graph.png", str(folder),
                        str(Path(directory) / "missing" / "x.svg")]
            for output in examples:
                with self.subTest(output=output):
                    self.rejected(self.base() + ["--output", output])

    def test_bad_filter(self):
        """Отклонить пробелы, управляющий символ и исключение корня."""
        for value in ["   ", "bad\nname", "odd"]:
            with self.subTest(value=value):
                self.rejected(self.base() + ["--filter", value])

    def test_ascii_and_filter(self):
        """Прочитать переключатель дерева и непустой фильтр."""
        args = arguments(self.base() + ["--ascii", "--filter", "is-number"])
        self.assertTrue(args.ascii_tree)
        self.assertEqual(args.filter, "is-number")

    def test_flag_values(self):
        """Переключатели не принимают произвольные значения."""
        for flag in ["--ascii", "--test"]:
            with self.subTest(flag=flag):
                self.rejected(self.base() + [flag, "yes"])

    def test_missing_required(self):
        """Потребовать имя, реестр и версию."""
        base = self.base()
        for index in [0, 2, 4]:
            with self.subTest(index=index):
                self.rejected(base[:index] + base[index + 2:])

    def test_unknown_option(self):
        """Отклонить неизвестную опцию."""
        self.rejected(self.base() + ["--unknown"])


if __name__ == "__main__":
    unittest.main()
