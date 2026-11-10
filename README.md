# Практическая работа № 2 — вариант 8

Дисциплина: «Конфигурационное управление».

## Текущий этап

Этап 5 (финальный): Graphviz DOT, SVG и ASCII-дерево.
Реализованы прямой и обратный анализ зависимостей npm.
Для обхода после разворота рёбер повторно используется рекурсивный BFS.

Рекурсия используется именно между уровнями BFS:
сначала полностью обрабатывается текущий уровень, затем следующий.
Это не DFS и не итеративная замена рекурсивного обхода.
Каждая вершина отмечается при добавлении в следующий уровень.
Связи с уже обнаруженными вершинами сохраняются.

## Требования и запуск

Python 3.10+, Bash для run.sh. Для SVG нужен Graphviz (команда dot).
Отдельная сборка не требуется.
Используется стандартная библиотека Python. npm, Node.js и библиотеки
анализа пакетов основная программа не вызывает и не импортирует.
Отдельный скрипт verification/compare_npm.py вызывает npm только
для независимой проверки результата.
Для настоящего реестра нужен интернет; автоматические тесты работают офлайн.

```bash
bash run.sh --help
bash run.sh --tests
```

Также поддерживается python -m src.main с теми же параметрами.
Необязательный GitHub Actions запускает те же тесты, демонстрацию
и проверку оформления. Он не является частью алгоритма.

## Семь базовых параметров и режимы анализа

| Параметр | Назначение | По умолчанию |
| --- | --- | --- |
| --package | Имя начального пакета | Обязательный |
| --repository | HTTP(S) URL реестра или путь JSON | Обязательный |
| --test | Читать локальный граф | Выключен |
| --version | Точная версия начального npm-пакета | Обязательный |
| --output | Путь SVG при --visualize | graph.svg |
| --ascii | Вывод ASCII-дерева | Выключен |
| --filter | Исключать пакеты с подстрокой в имени | Пустая строка |
| --reverse | Искать обратные зависимости | Выключен |
| --roots | JSON исходных пакетов для npm --reverse | Не задан |
| --visualize | Сохранить SVG и исходный DOT | Выключен |
| --dot | Исполняемый файл Graphviz | dot |

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
--output требует расширение .svg и существующую родительскую папку.
--visualize создаёт SVG и рядом одноимённый файл .dot.
--ascii заменяет список смежности ASCII-деревом; его можно совместить
с --visualize. Без --visualize Graphviz не требуется.
Обратный анализ включается --reverse. Для npm требуется --roots.

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

## Обратные зависимости

Режим --reverse находит пакеты, которые требуют выбранный пакет
непосредственно или через цепочку зависимостей.
Начальный пакет исключается из итогового списка зависимых.
В строках обратного графа C -> B означает, что B требует C.

### Полный тестовый репозиторий

Сначала разворачиваются рёбра всего JSON-файла, затем выполняется тот же
рекурсивный BFS. Нельзя разворачивать только прямой подграф выбранного
пакета: тогда пакеты, которые зависят от него, могли бы потеряться.

```bash
bash run.sh --package C --version 1.0.0 --test --reverse \
  --repository tests/fixtures/chain.json
```

Результат: C -> B, B -> A, A -> (нет), итоговый список B, A.

```bash
bash run.sh --package A --version 1.0.0 --test --reverse \
  --repository tests/fixtures/cycle.json
bash run.sh --package D --version 1.0.0 --test --reverse --filter B \
  --repository tests/fixtures/diamond.json
```

Цикл завершается; при фильтре B в ромбе остаётся обратный путь D, C, A.
Изолированные вершины сохраняются, пустой список зависимых допустим.

### Настоящий npm: явно определённая область

Метаданные одного пакета содержат его исходящие зависимости, но не
полный список всех пакетов npm, которые от него зависят.
Для обратного поиска нужно явно определить анализируемый набор пакетов.
Используется JSON-файл --roots с точными исходными версиями:

```json
[
  {"package": "is-odd", "version": "3.0.1"},
  {"package": "is-even", "version": "1.0.0"}
]
```

Сначала объединяются полные транзитивные графы указанных исходных пакетов
и самого запрошенного пакета. Затем разворачиваются все рёбра объединения
и выполняется рекурсивный BFS от запрошенной пары (имя, версия).
Каталоги переиспользуются через общий кэш.

Это поиск в явно заданной области, а не глобальный поиск по всему npm.
Пакеты вне этой области в результат не входят.
Без --roots настоящий режим --reverse отклоняется с пояснением.
Для --test область уже полностью задана JSON-файлом, --roots не нужен.

```bash
bash run.sh --package is-number --version 6.0.0 --reverse \
  --repository https://registry.npmjs.org \
  --roots tests/fixtures/npm_roots.json
bash run.sh --package is-buffer --version 1.1.6 --reverse \
  --repository https://registry.npmjs.org \
  --roots tests/fixtures/npm_roots.json
```

В первом примере зависимый пакет — is-odd@3.0.1.
Во втором находится цепочка через kind-of, is-number, is-odd и is-even.
Фильтр применяется к именам пакетов. Исключённые исходные пакеты
и зависимости не скачиваются, пути через них отсекаются.

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

- build_parser() — описание базовых параметров и режимов графа.
- validate_package(args) — структура и длина имени.
- validate_registry_url(address) — схема, хост и пробелы URL.
- validate_url_details(url) — лишние части URL и порт.
- validate_repository(args) — выбор проверки файла или URL.
- validate_version(args) — точный SemVer начального пакета.
- validate_output(args) — путь будущего SVG.
- validate_filter(args) — допустимость подстроки.
- validate_reverse_options(args) — область обратного анализа.
- arguments(argv=None) — чтение и проверка настроек.
- root_node(args) — буквенное имя или пара (имя, версия).
- selected_graph(args) — прямой или обратный BFS по нужному источнику.
- output_graph(args, graph) — список, ASCII, SVG и итог обратного поиска.
- main(argv=None) — запуск и обработка ошибок.

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
- reverse_graph(graph) — разворот рёбер всего переданного графа.

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

### src/reverse.py

- validate_root(record) — проверка имени и точной версии исходного пакета.
- read_roots(path) — чтение списка исходных пакетов без повторов.
- universe_graph(repository, target, roots, excluded="") — объединение
  транзитивных графов запроса и заданных исходных пакетов.

## Проверки и демонстрации

```bash
bash run.sh --tests
python tests/demo_cli.py
python tests/check_style.py
```

Всего 93 автоматических теста: 16 CLI, 10 HTTP/метаданных,
12 графа, 12 SemVer, 8 ленивого источника npm, 15 обратного анализа,
17 визуализации и 3 нормализации контрольного вывода npm.
Тесты и демонстрационный скрипт работают офлайн с явно тестовыми ответами.
Реальные запросы отдельно проверены при подготовке архива.

[Примеры третьего этапа](docs/stage3-examples.md)

[Примеры и результаты четвёртого этапа](docs/stage4-examples.md)

Дополнительно собственные правила диапазонов сверены с node-semver
в 2369 контрольных сочетаниях версий и требований без расхождений.
Эталон использовался только вне приложения для проверки разработки;
в проекте нет зависимости от этой библиотеки.
Это не утверждение о полном покрытии всех расширений npm.

Официальные спецификации: https://semver.org/ и
https://github.com/npm/node-semver#ranges.

Коды завершения: 0 — успех, 1 — ошибка выполнения, 2 — ошибка CLI.
GitHub Actions — необязательная автоматизация тех же проверок.

## Визуализация: Graphviz и ASCII

Установка Graphviz: https://graphviz.org/download/.
На Windows установите Graphviz и добавьте его папку bin в PATH,
либо передайте полный путь к dot.exe через --dot.
Для Ubuntu/WSL: sudo apt-get install graphviz.
Проверка установки: dot -V. Java и PlantUML не нужны.

```bash
mkdir -p out
bash run.sh --package A --version 1.0.0 --test \
  --repository tests/fixtures/diamond.json --ascii --visualize \
  --output out/diamond.svg
bash run.sh --package A --version 1.0.0 --test \
  --repository tests/fixtures/cycle.json --ascii
bash run.sh --package C --version 1.0.0 --test --reverse \
  --repository tests/fixtures/chain.json --ascii --visualize \
  --output out/reverse.svg
bash run.sh --package is-even --version 1.0.0 \
  --repository https://registry.npmjs.org --ascii --visualize \
  --output out/is-even.svg
```

SVG открывается браузером. Исходный DOT можно открыть текстовым редактором.
В ASCII [cycle] отмечает возврат к предку, [shown] — ранее показанную
общую вершину. Поэтому циклы и ромбы не приводят к бесконечному выводу.
Граф строится рекурсивным BFS; дерево отображает уже построенный граф.

### src/render.py

- to_dot(graph) — DOT с безопасными подписями и отдельными ID вершин.
- validate_svg(data) — проверка XML и корневого элемента SVG.
- render_svg(graph, output, dot="dot") — запись DOT и запуск Graphviz.
- to_ascii(graph, root) — дерево с пометками циклов и общих вершин.
- Внутренняя visit(node, prefix, connector, ancestors) строит строки дерева.

Graphviz запускается без shell, таймаут — 60 секунд.
Отсутствующий dot, ошибка рендеринга и некорректный SVG дают код 1.

## Сравнение с нативным npm

[Результаты трёх реальных примеров](docs/comparison.md).
Для is-number@6.0.0, is-odd@3.0.1 и is-even@1.0.0 совпали множества
вершин и рёбер с конкретными версиями. Результат привязан к дате отчёта.

Для повторения нужны Linux/WSL, Python, Node.js/npm, Graphviz и интернет:

```bash
python verification/compare_npm.py
```

Скрипт создаёт out/, сохраняет DOT, SVG, наше ASCII-дерево, сырой JSON
и текст npm ls, а также comparison.md и comparison.json.
Установка контрольных пакетов выполняется с --ignore-scripts.
Проект-обёртка исключается при сравнении; повторные записи npm объединяются.
Скрипт завершится с кодом 1 при расхождении, с кодом 0 при совпадении.
Файлы out/, node_modules и кэши не включаются в репозиторий.

### verification

native.py: read_node() восстанавливает граф npm ls; native_graph() убирает
служебный корень; graph_edges() выделяет множество рёбер.
compare_npm.py: main() выполняет три сравнения; остальные функции
готовят контрольную установку, сохраняют результаты и составляют отчёт.
Этот код не используется приложением при анализе зависимостей.

## Необязательный запуск примеров на GitHub

После загрузки последнего этапа можно открыть Actions, выбрать
Render and compare examples, нажать Run workflow и дождаться завершения.
Внизу запуска в Artifacts доступен npm-graph-examples с SVG и отчётами.
Эта проверка требует сети; выполнять её для использования программы
не обязательно. Check project запускает только офлайн-проверки.
