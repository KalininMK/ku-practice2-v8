"""Три SVG и отдельное контрольное сравнение со штатным npm ls."""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.graph import bfs, node_label
from src.npm_graph import NpmRepository
from src.render import render_svg, to_ascii
from verification.native import graph_edges, native_graph

REGISTRY = "https://registry.npmjs.org"
CASES = [("is-number", "6.0.0"), ("is-odd", "3.0.1"), ("is-even", "1.0.0")]
COMMAND_TIMEOUT = 120


def run(command, directory):
    """Выполнить только контрольную внешнюю команду и проверить успех."""
    result = subprocess.run(command, cwd=directory, capture_output=True,
                            text=True, encoding="utf-8", errors="replace",
                            timeout=COMMAND_TIMEOUT)
    if result.returncode:
        raise ValueError(result.stderr or result.stdout)
    return result.stdout


def reference_tree(name, version, folder):
    """Установить пакет в отдельный каталог и вызвать npm ls."""
    directory = folder / "native" / name
    directory.mkdir(parents=True, exist_ok=True)
    package = {"name": f"reference-{name}", "version": "1.0.0", "private": True}
    (directory / "package.json").write_text(
        json.dumps(package), encoding="utf-8")
    run(["npm", "install", f"{name}@{version}", "--ignore-scripts",
         "--no-audit", "--no-fund", "--omit=dev", "--omit=optional",
         "--legacy-peer-deps", "--package-lock=false", "--save-exact",
         "--registry", REGISTRY,
         "--cache", str(folder / ".npm-cache")], directory)
    command = ["npm", "ls", "--all", "--omit=dev", "--omit=optional"]
    data = run(command + ["--json"], directory)
    text = run(command + ["--unicode=false"], directory)
    text = text.replace(str(directory), "<reference project directory>")
    (folder / f"npm-{name}.json").write_text(data, encoding="utf-8")
    (folder / f"npm-{name}.txt").write_text(text, encoding="utf-8")
    return native_graph(json.loads(data), name, version), text


def compare_case(repository, name, version, folder, dot):
    """Сравнить одинаковые пакеты и версии по вершинам и рёбрам."""
    root = name, version
    graph = bfs(repository.dependencies, root)
    render_svg(graph, folder / f"{name}.svg", dot)
    (folder / f"{name}-tree.txt").write_text(to_ascii(graph, root) + "\n",
                                           encoding="utf-8")
    reference, text = reference_tree(name, version, folder)
    same = set(graph) == set(reference)
    same = same and graph_edges(graph) == graph_edges(reference)
    edges = [f"{node_label(a)} -> {node_label(b)}"
             for a, b in sorted(graph_edges(graph))]
    return {"package": name, "version": version, "equal": same,
            "nodes": len(graph), "edges": len(graph_edges(graph)),
            "own_edges": edges, "native_tree": text.strip(),
            "native_edges": [f"{node_label(a)} -> {node_label(b)}"
                             for a, b in sorted(graph_edges(reference))]}


def case_lines(row):
    """Оформить один фактически проверенный пример."""
    result = "Совпало" if row["equal"] else "Есть расхождения"
    return [f"## {row['package']}@{row['version']}", "",
            f"Вершин: {row['nodes']}; рёбер: {row['edges']}.", "",
            "Наши связи:", "```text", "\n".join(row["own_edges"])
            or "(нет зависимостей)", "```", "", "Штатные связи:",
            "```text", "\n".join(row["native_edges"])
            or "(нет зависимостей)", "```", "", "npm ls --all:",
            "```text", row["native_tree"], "```", "", result + ".", ""]


def write_report(rows, folder, dot):
    """Сохранить фактические результаты сравнения без ложных совпадений."""
    npm_version = run(["npm", "--version"], folder).strip()
    graphviz_version = subprocess.run(
        [dot, "-V"], capture_output=True, text=True, check=True
    ).stderr.strip()
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    lines = ["# Сравнение с npm ls", "",
             "Дата: " + timestamp,
             "", f"npm: {npm_version}; Node.js: "
             + run(["node", "--version"], folder).strip(),
             f"Graphviz: {graphviz_version}.", "", "Реестр: " + REGISTRY, "",
             "Приложение строит граф собственным кодом через HTTP.",
             "npm вызывается только этим отдельным контрольным скриптом.",
             "Сравниваются множества вершин и рёбер с конкретными версиями.",
             "Служебный корень проекта npm исключён из сравнения.", ""]
    for row in rows:
        lines += case_lines(row)
    lines += ["## Условия сравнения", "", "Использованы --ignore-scripts,",
              "--omit=dev, --omit=optional и --legacy-peer-deps при установке.",
              "Это согласует сравнение с анализируемым полем dependencies.",
              "Абсолютный путь контрольного проекта в первой строке заменён",
              "на обозначение каталога; имена, версии и связи не менялись.",
              "Совпадение на этих примерах не означает реализацию всего npm.",
              "Полный вывод npm ls --json сохранён в out/npm-*.json.", ""]
    (folder / "comparison.md").write_text("\n".join(lines), encoding="utf-8")
    (folder / "comparison.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    """Запустить контроль отдельно от приложения, в Linux или WSL."""
    if os.name == "nt":
        raise SystemExit("Этот контроль запускается в WSL или GitHub Actions")
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "out"))
    parser.add_argument("--dot", default="dot")
    args = parser.parse_args()
    folder = Path(args.output).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    repository = NpmRepository(REGISTRY)
    rows = []
    for name, version in CASES:
        row = compare_case(repository, name, version, folder, args.dot)
        rows.append(row)
        status = "совпало" if row["equal"] else "различия"
        print(f"{name}@{version}: {status}", flush=True)
    write_report(rows, folder, args.dot)
    return 0 if all(row["equal"] for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
