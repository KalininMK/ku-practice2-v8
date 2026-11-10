# Сравнение с npm ls

Дата: 2026-11-11T02:50:09+03:00

npm: 11.9.0; Node.js: v24.22.1
Graphviz: dot - graphviz version 2.42.4 (0).

Реестр: https://registry.npmjs.org

Приложение строит граф собственным кодом через HTTP.
npm вызывается только этим отдельным контрольным скриптом.
Сравниваются множества вершин и рёбер с конкретными версиями.
Служебный корень проекта npm исключён из сравнения.

## is-number@6.0.0

Вершин: 1; рёбер: 0.

Наши связи:
```text
(нет зависимостей)
```

Штатные связи:
```text
(нет зависимостей)
```

npm ls --all:
```text
reference-is-number@1.0.0 <reference project directory>
`-- is-number@6.0.0
```

Совпало.

## is-odd@3.0.1

Вершин: 2; рёбер: 1.

Наши связи:
```text
is-odd@3.0.1 -> is-number@6.0.0
```

Штатные связи:
```text
is-odd@3.0.1 -> is-number@6.0.0
```

npm ls --all:
```text
reference-is-odd@1.0.0 <reference project directory>
`-- is-odd@3.0.1
  `-- is-number@6.0.0
```

Совпало.

## is-even@1.0.0

Вершин: 5; рёбер: 4.

Наши связи:
```text
is-even@1.0.0 -> is-odd@0.1.2
is-number@3.0.0 -> kind-of@3.2.2
is-odd@0.1.2 -> is-number@3.0.0
kind-of@3.2.2 -> is-buffer@1.1.6
```

Штатные связи:
```text
is-even@1.0.0 -> is-odd@0.1.2
is-number@3.0.0 -> kind-of@3.2.2
is-odd@0.1.2 -> is-number@3.0.0
kind-of@3.2.2 -> is-buffer@1.1.6
```

npm ls --all:
```text
reference-is-even@1.0.0 <reference project directory>
`-- is-even@1.0.0
  `-- is-odd@0.1.2
    `-- is-number@3.0.0
      `-- kind-of@3.2.2
        `-- is-buffer@1.1.6
```

Совпало.

## Условия сравнения

Использованы --ignore-scripts,
--omit=dev, --omit=optional и --legacy-peer-deps при установке.
Это согласует сравнение с анализируемым полем dependencies.
Абсолютный путь контрольного проекта в первой строке заменён
на обозначение каталога; имена, версии и связи не менялись.
Совпадение на этих примерах не означает реализацию всего npm.
Полный вывод npm ls --json сохранён в out/npm-*.json.
