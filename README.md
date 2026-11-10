# Практическая работа № 2 — вариант 8

Дисциплина: «Конфигурационное управление».

## Текущий этап

Этап 3: граф транзитивных зависимостей, BFS с рекурсией,
циклы, фильтрация и локальный тестовый репозиторий.

Рекурсия используется именно между уровнями BFS:
сначала полностью обрабатывается текущий уровень, затем следующий.
Это не DFS и не итеративная замена рекурсивного обхода.
Каждая вершина отмечается при добавлении в следующий уровень.
Связи с уже обнаруженными вершинами сохраняются.

## Требования и запуск

Python 3.10+, Bash для run.sh. Отдельная сборка не требуется.
Используется стандартная библиотека Python. npm, Node.js и библиотеки
анализа пакетов программа не вызывает и не импортирует.
Для настоящего реестра нужен интернет; автоматические тесты работают офлайн.

```bash
bash run.sh --help
bash run.sh --tests
```

Также поддерживается python -m src.main с теми же параметрами.
Необязательный GitHub Actions запускает те же тесты, демонстрацию
и проверку оформления. Он не является частью алгоритма.

## Семь параметров

| Параметр | Назначение | По умолчанию |
| --- | --- | --- |
| --package | Имя начального пакета | Обязательный |
| --repository | HTTP(S) URL реестра или путь JSON | Обязательный |
| --test | Читать локальный граф | Выключен |
| --version | Точная версия начального npm-пакета | Обязательный |
| --output | Путь будущего SVG | graph.svg |
| --ascii | Режим будущего ASCII-дерева | Выключен |
| --filter | Исключать пакеты с подстрокой в имени | Пустая строка |

--test и --ascii — переключатели без значений.
Имена npm проверяются на структуру, регистр и длину до 214 символов.
Поддерживается @scope/package. Имена тестового графа состоят из A-Z.
Фильтр регистрозависимый и применяется к имени, без номера версии.
Пустой фильтр отключён. Исключение начального пакета является ошибкой.
Удалённая вершина не посещается, путь через неё отсекается.
Другие разрешённые пути к общим зависимостям сохраняются.
Исключённые зависимости npm не вызывают HTTP-запросов.

--version начального пакета требует точный SemVer, а не latest или ^1.0.0.
В тестовом режиме версия проверяется, но не меняет JSON-граф:
его вершины по условию задания имеют буквенные имена без версий.
--output пока только проверяется: .svg и существующая родительская папка.
Изображение и ASCII-дерево появятся на этапе 5.
Обратный анализ будет добавлен на этапе 4.

## Тестовый репозиторий

```json
{
  "A": ["B", "C"],
  "B": ["D"],
  "C": ["D"],
  "D": []
}
```

Все упомянутые вершины должны быть объявлены ключами.
JSON содержит данные, настройки поступают через командную строку.

```bash
bash run.sh --package A --version 1.0.0 --test \
  --repository tests/fixtures/diamond.json
```

Ожидаемый порядок строк: A, B, C, D.

```bash
bash run.sh --package A --version 1.0.0 --test \
  --repository tests/fixtures/diamond.json --filter B
```

Ожидаются A -> C, C -> D, D -> (нет).
Общая вершина D остаётся, поскольку существует путь через C.

Другие случаи:

```bash
bash run.sh --package A --version 1.0.0 --test \
  --repository tests/fixtures/chain.json
bash run.sh --package A --version 1.0.0 --test \
  --repository tests/fixtures/cycle.json
bash run.sh --package A --version 1.0.0 --test \
  --repository tests/fixtures/isolated.json
bash run.sh --package A --version 1.0.0 --test \
  --repository tests/fixtures/self_cycle.json
```

## Настоящий реестр npm

```bash
bash run.sh --package is-odd --version 3.0.1 \
  --repository https://registry.npmjs.org
bash run.sh --package is-even --version 1.0.0 \
  --repository https://registry.npmjs.org
bash run.sh --package is-even --version 1.0.0 --filter is-number \
  --repository https://registry.npmjs.org
```

Вершина npm представлена парой (имя, конкретная версия).
Это позволяет различать разные версии одного пакета.
При выводе используется подпись name@version.
Каталог каждого имени загружается не более одного раза за анализ.
Требования берутся из dependencies выбранной записи версии.
Для каждого требования выбирается максимальная подходящая версия.
dist-tags зависимостей разрешаются через каталог реестра.

Собственная реализация диапазонов поддерживает точные версии,
сравнения < <= > >= =, AND через пробел, OR через ||,
caret ^, tilde ~, wildcard x/X/*, частичные версии и отдельные
дефисные диапазоны. Учитываются prerelease и метаданные сборки.
Неподдерживаемое требование даёт ошибку, а не произвольную версию.

## Ограничения модели

Анализируется поле dependencies. devDependencies, peerDependencies
и optionalDependencies отдельно не включаются.
Git-, file-, workspace-зависимости и npm:-алиасы не поддерживаются.
Сложные или нестрогие расширения грамматики диапазонов могут отклоняться.
Выбор версии выполняется независимо для каждого ребра; не моделируются
физическая раскладка node_modules, hoisting, lock-файл и полный solver npm.
Состояние реестра может меняться; кэш фиксирует каталог в пределах анализа.

Глубина вызовов BFS равна числу уровней. При превышении ограничения
рекурсии Python программа выдаёт понятную ошибку с кодом 1.
Большая ширина одного уровня не увеличивает глубину рекурсии.

## Функции и устройство

### src/main.py

- build_parser() — описание семи параметров.
- validate_package(args) — структура и длина имени.
- validate_registry_url(address) — схема, хост и пробелы URL.
- validate_url_details(url) — лишние части URL и порт.
- validate_repository(args) — выбор проверки файла или URL.
- validate_version(args) — точный SemVer начального пакета.
- validate_output(args) — путь будущего SVG.
- validate_filter(args) — допустимость подстроки.
- arguments(argv=None) — чтение и проверка настроек.
- selected_graph(args) — BFS над JSON или ленивым источником npm.
- main(argv=None) — вывод результата и обработка ошибок.

При argv=None читается командная строка, в тестах передаётся список.

### src/registry.py

- metadata_url(repository, package, version) — URL одной версии.
- fetch_json(url, description) — JSON по HTTP и обработка ошибок.
- fetch_metadata(package, version, repository) — запись одной версии.
- fetch_catalog(package, repository) — каталог всех версий пакета.
- validate_dependencies(dependencies) — проверка поля dependencies.
- validate_metadata(metadata, package, version) — проверка записи.
- direct_dependencies(package, version, repository) — прямые требования.

Таймаут каждого HTTP-запроса — 30 секунд.

### src/graph.py

- node_name(node) — имя без версии для фильтрации.
- node_label(node) — подпись name@version или буквенное имя.
- load_test_graph(path) — чтение и проверка JSON, включая UTF-8 BOM.
- bfs(graph, start, excluded="") — рекурсивный BFS по уровням.
- Внутренняя visit_level(frontier) обрабатывает уровень и вызывает себя.
- print_graph(graph) — вывод рёбер в порядке обнаружения вершин.

bfs принимает словарь соседей или функцию получения соседей.

### src/npm_graph.py

- NpmRepository(address, excluded="") — кэши каталогов и выбранных версий.
- catalog(name) — загрузка и проверка каталога одного имени.
- resolve(name, requirement) — версия по диапазону или dist-tag.
- dependencies(node) — соседи конкретной версии с ранней фильтрацией.

### src/semver.py

- version_parts(text) — строгая версия без метаданных сборки.
- version_key(text) — порядок версий с prerelease-идентификаторами.
- numeric_prefix(groups) — числовая часть частичной версии.
- partial_version(text) — дополнение пропущенных частей нулями.
- increment(base, position) — увеличение компонента и обнуление младших.
- compatible_bounds(symbol, base, precision) — разворот ^ и ~.
- wildcard_bounds(symbol, base, precision) — сравнения с wildcard.
- expand_token(token) — разворот одного требования.
- hyphen_bounds(low, high) — отдельный диапазон с дефисом.
- compile_range(requirement) — альтернативы элементарных сравнений.
- matches_branch(version, comparisons) — AND и допуск prerelease.
- satisfies(version, requirement) — принадлежность диапазону.
- select_version(versions, requirement) — максимальная совместимая версия.

## Проверки и демонстрации

```bash
bash run.sh --tests
python tests/demo_cli.py
python tests/check_style.py
```

Всего 58 автоматических тестов: 16 CLI, 10 HTTP/метаданных,
12 графа, 12 SemVer и 8 ленивого источника npm.
Тесты и демонстрационный скрипт работают офлайн с явно тестовыми ответами.
Реальные запросы отдельно проверены при подготовке архива.

[Примеры и результаты контрольного запуска](docs/stage3-examples.md)

Дополнительно собственные правила диапазонов сверены с node-semver
в 2369 контрольных сочетаниях версий и требований без расхождений.
Эталон использовался только вне приложения для проверки разработки;
в проекте нет зависимости от этой библиотеки.
Это не утверждение о полном покрытии всех расширений npm.

Официальные спецификации: https://semver.org/ и
https://github.com/npm/node-semver#ranges.

Коды завершения: 0 — успех, 1 — ошибка выполнения, 2 — ошибка CLI.
GitHub Actions — необязательная автоматизация тех же проверок.
