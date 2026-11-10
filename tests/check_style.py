"""Проверка размеров строк, функций и числа аргументов."""

import ast
from pathlib import Path

LINE_LIMIT = 80
FUNCTION_LIMIT = 40
ARGUMENT_LIMIT = 7
FILE_LIMIT = 1000


def check_file(path):
    """Вернуть замечания к одному файлу Python."""
    source = path.read_text(encoding="utf-8")
    issues = []
    lines = source.splitlines()
    if len(lines) > FILE_LIMIT:
        issues.append(f"{path}: больше {FILE_LIMIT} строк")
    for number, line in enumerate(lines, 1):
        if len(line) > LINE_LIMIT:
            issues.append(f"{path}:{number}: строка длиннее {LINE_LIMIT}")
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.end_lineno - node.lineno + 1 > FUNCTION_LIMIT:
            issues.append(f"{path}:{node.lineno}: слишком длинная функция")
        count = (len(node.args.args) + len(node.args.posonlyargs)
                 + len(node.args.kwonlyargs))
        if count > ARGUMENT_LIMIT:
            issues.append(f"{path}:{node.lineno}: слишком много аргументов")
        if ast.get_docstring(node) is None:
            issues.append(f"{path}:{node.lineno}: отсутствует docstring")
    return issues


def main():
    """Проверить исходники и тестовые скрипты."""
    root = Path(__file__).resolve().parents[1]
    paths = sorted((root / "src").rglob("*.py"))
    paths += sorted((root / "tests").rglob("*.py"))
    paths += sorted((root / "verification").rglob("*.py"))
    issues = [issue for path in paths for issue in check_file(path)]
    if issues:
        raise SystemExit("\n".join(issues))
    print("Ограничения размеров Python-кода соблюдены")


if __name__ == "__main__":
    main()
