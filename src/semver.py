"""Собственные правила SemVer и диапазонов npm, без внешних библиотек."""

import operator
import re

CORE_PARTS = 3
NUMBER = r"(?:0|[1-9][0-9]*)"
PRERELEASE = rf"(?:{NUMBER}|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*)"
SEMVER = (
    rf"{NUMBER}\.{NUMBER}\.{NUMBER}"
    rf"(?:-{PRERELEASE}(?:\.{PRERELEASE})*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
)
PARTIAL = r"v?([0-9xX*]+)(?:\.([0-9xX*]+))?(?:\.([0-9xX*]+))?"
OPERATORS = {"=": operator.eq, ">": operator.gt, ">=": operator.ge,
             "<": operator.lt, "<=": operator.le}


def version_parts(text):
    """Разобрать строгую версию, отбросив метаданные сборки."""
    if not isinstance(text, str) or not re.fullmatch(SEMVER, text):
        raise ValueError(f"Некорректная версия SemVer: {text}")
    clean = text.split("+", maxsplit=1)[0]
    core, _, prerelease = clean.partition("-")
    return tuple(map(int, core.split("."))), tuple(prerelease.split("."))


def version_key(text):
    """Получить ключ порядка с числовыми prerelease-компонентами."""
    core, prerelease = version_parts(text)
    if prerelease == ("",):
        return core, True, ()
    identifiers = tuple((False, int(part)) if part.isdigit() else (True, part)
                        for part in prerelease)
    return core, False, identifiers


def numeric_prefix(groups):
    """Прочитать числовой префикс без чисел после wildcard."""
    parts = []
    wildcard = False
    for part in groups:
        if part is None or part in {"x", "X", "*"}:
            wildcard = True
            continue
        if wildcard or not re.fullmatch(NUMBER, part):
            raise ValueError("Неправильная частичная версия")
        parts.append(int(part))
    return parts


def partial_version(text):
    """Дополнить частичную версию нулями и вернуть точность."""
    normalized = text.removeprefix("v")
    if re.fullmatch(SEMVER, normalized):
        return normalized, CORE_PARTS
    match = re.fullmatch(PARTIAL, text)
    if not match:
        raise ValueError(f"Неподдерживаемое требование версии: {text}")
    parts = numeric_prefix(match.groups())
    precision = len(parts)
    parts += [0] * (CORE_PARTS - precision)
    return ".".join(map(str, parts)), precision


def increment(base, position):
    """Увеличить выбранную часть и обнулить младшие части."""
    core = list(version_parts(base)[0])
    core[position] += 1
    for index in range(position + 1, CORE_PARTS):
        core[index] = 0
    return ".".join(map(str, core))


def compatible_bounds(symbol, base, precision):
    """Развернуть caret или tilde в пару сравнений."""
    if not precision:
        return []
    if symbol == "~":
        position = min(precision - 1, 1)
    else:
        core = version_parts(base)[0]
        position = next((index for index in range(precision)
                         if core[index]), precision - 1)
    return [(">=", base), ("<", increment(base, position) + "-0")]


def wildcard_bounds(symbol, base, precision):
    """Развернуть обычное сравнение с частичной версией."""
    if precision == CORE_PARTS:
        return [(symbol or "=", base)]
    if not precision:
        return [("<", "0.0.0-0")] if symbol in {"<", ">"} else []
    upper = increment(base, precision - 1)
    if symbol in {"", "="}:
        return [(">=", base), ("<", upper + "-0")]
    rules = {">=": (">=", base), ">": (">=", upper),
             "<=": ("<", upper + "-0"), "<": ("<", base + "-0")}
    return [rules[symbol]]


def expand_token(token):
    """Развернуть один оператор диапазона npm."""
    match = re.fullmatch(r"(\^|~|<=|>=|<|>|=)?(.+)", token)
    if not match:
        raise ValueError(f"Неподдерживаемый диапазон: {token}")
    symbol, text = match.groups()
    base, precision = partial_version(text)
    if symbol in {"^", "~"}:
        return compatible_bounds(symbol, base, precision)
    return wildcard_bounds(symbol or "", base, precision)


def hyphen_bounds(low, high):
    """Развернуть включительный диапазон с дефисом."""
    lower, lower_precision = partial_version(low)
    upper, upper_precision = partial_version(high)
    result = [(">=", lower)] if lower_precision else []
    if upper_precision == CORE_PARTS:
        result.append(("<=", upper))
    elif upper_precision:
        result.append(("<", increment(upper, upper_precision - 1) + "-0"))
    return result


def compile_range(requirement):
    """Получить альтернативы сравнений из диапазона npm."""
    if not isinstance(requirement, str):
        raise ValueError("Требование версии должно быть строкой")
    alternatives = []
    for branch in requirement.strip().split("||"):
        branch = branch.strip()
        hyphen = re.fullmatch(r"(\S+)\s+-\s+(\S+)", branch)
        if hyphen:
            alternatives.append(hyphen_bounds(*hyphen.groups()))
            continue
        branch = re.sub(r"(<=|>=|<|>|=|\^|~)\s+", r"\1", branch)
        tokens = branch.split() or ["*"]
        comparisons = []
        for token in tokens:
            comparisons.extend(expand_token(token))
        alternatives.append(comparisons)
    return alternatives


def matches_branch(version, comparisons):
    """Проверить сравнения и правила допуска prerelease."""
    key = version_key(version)
    if not all(OPERATORS[symbol](key, version_key(target))
               for symbol, target in comparisons):
        return False
    if key[1]:
        return True
    return any(not version_key(target)[1]
               and version_key(target)[0] == key[0]
               for _, target in comparisons)


def satisfies(version, requirement):
    """Проверить принадлежность версии диапазону."""
    alternatives = compile_range(requirement)
    return any(matches_branch(version, branch) for branch in alternatives)


def select_version(versions, requirement):
    """Выбрать наибольшую подходящую строгую SemVer-версию."""
    alternatives = compile_range(requirement)
    candidates = []
    for version in versions:
        if not isinstance(version, str) or not re.fullmatch(SEMVER, version):
            continue
        if any(matches_branch(version, branch) for branch in alternatives):
            candidates.append(version)
    if not candidates:
        raise ValueError(f"Нет версии, подходящей под {requirement!r}")
    return max(sorted(candidates), key=version_key)
