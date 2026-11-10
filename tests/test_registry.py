"""Проверки HTTP, npm-метаданных и вывода второго этапа."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from src.main import main
from src.registry import direct_dependencies, fetch_metadata

METADATA = {
    "name": "is-odd", "version": "3.0.1",
    "dependencies": {"is-number": "^6.0.0"},
}
BASE = ["--package", "is-odd", "--repository",
        "https://registry.npmjs.org", "--version", "3.0.1"]


def response(metadata):
    """Создать ответ HTTP в памяти."""
    return io.BytesIO(json.dumps(metadata).encode("utf-8"))


class RegistryTests(unittest.TestCase):
    """Проверки выполняются без сети и без npm."""

    def test_download(self):
        """Использовать выбранную версию и сохранить её требования."""
        with patch("src.registry.urlopen",
                   return_value=response(METADATA)) as opened:
            result = direct_dependencies(
                "is-odd", "3.0.1", "https://registry.npmjs.org/"
            )
        self.assertEqual(result, {"is-number": "^6.0.0"})
        request = opened.call_args.args[0]
        self.assertEqual(request.full_url,
                         "https://registry.npmjs.org/is-odd/3.0.1")
        self.assertEqual(opened.call_args.kwargs["timeout"], 30)

    def test_scoped_url(self):
        """Кодировать область npm и учитывать пользовательский URL."""
        with patch("src.registry.urlopen",
                   return_value=response(METADATA)) as opened:
            fetch_metadata("@scope/package", "3.0.1",
                           "https://example.org/registry/")
        self.assertEqual(
            opened.call_args.args[0].full_url,
            "https://example.org/registry/%40scope%2Fpackage/3.0.1",
        )

    def test_http_errors(self):
        """Объяснить отсутствие пакета и другие ошибки HTTP."""
        for status in [404, 503]:
            error = HTTPError("https://example.org", status, "error", {}, None)
            with self.subTest(status=status):
                with patch("src.registry.urlopen", side_effect=error):
                    with self.assertRaises(ValueError):
                        fetch_metadata("is-odd", "3.0.1",
                                       "https://example.org")

    def test_network_error(self):
        """Превратить сетевую ошибку в понятное сообщение."""
        with patch("src.registry.urlopen", side_effect=URLError("offline")):
            with self.assertRaisesRegex(OSError, "недоступен"):
                fetch_metadata("is-odd", "3.0.1", "https://example.org")

    def test_invalid_json(self):
        """Не принимать ответ, который не является JSON."""
        with patch("src.registry.urlopen", return_value=io.BytesIO(b"bad")):
            with self.assertRaisesRegex(ValueError, "не является JSON"):
                fetch_metadata("is-odd", "3.0.1", "https://example.org")

    def test_invalid_metadata(self):
        """Проверить тип данных, имя, версию и зависимости ответа."""
        examples = [[], {}, {**METADATA, "name": "another"},
                    {**METADATA, "version": "1.0.0"},
                    {**METADATA, "dependencies": []},
                    {**METADATA, "dependencies": {"lib": 1}},
                    {**METADATA, "dependencies": {"": "1.0.0"}}]
        for metadata in examples:
            with self.subTest(metadata=metadata):
                with patch("src.registry.urlopen",
                           return_value=response(metadata)):
                    with self.assertRaises(ValueError):
                        direct_dependencies("is-odd", "3.0.1",
                                            "https://example.org")

    def test_empty_dependencies(self):
        """Отсутствие dependencies означает пустой список требований."""
        metadata = {"name": "is-odd", "version": "3.0.1",
                    "devDependencies": {"test-tool": "1.0.0"}}
        with patch("src.registry.urlopen", return_value=response(metadata)):
            self.assertEqual(direct_dependencies(
                "is-odd", "3.0.1", "https://example.org"
            ), {})

    def test_main_output(self):
        """Вывести прямые требования в стабильном порядке."""
        output = io.StringIO()
        with patch("src.main.direct_dependencies",
                   return_value={"z-dep": "^1.0.0", "a-dep": "2.0.0"}):
            with redirect_stdout(output):
                code = main(BASE)
        self.assertEqual(code, 0)
        self.assertEqual(output.getvalue(), "a-dep: 2.0.0\nz-dep: ^1.0.0\n")

    def test_main_error(self):
        """Ошибки выполнения возвращают код 1 без traceback."""
        errors = io.StringIO()
        with patch("src.main.direct_dependencies",
                   side_effect=OSError("Нет соединения")):
            with redirect_stderr(errors):
                code = main(BASE)
        self.assertEqual(code, 1)
        self.assertIn("Нет соединения", errors.getvalue())

    def test_test_mode_pending(self):
        """Пояснить, что анализ JSON появится следующим этапом."""
        errors = io.StringIO()
        argv = BASE + ["--package", "A", "--test", "--repository",
                       "tests/fixtures/chain.json"]
        with redirect_stderr(errors):
            code = main(argv)
        self.assertEqual(code, 1)
        self.assertIn("этапе 3", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
