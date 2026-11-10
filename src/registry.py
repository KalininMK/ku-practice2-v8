"""Получение метаданных npm собственным HTTP-клиентом."""

import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

NETWORK_TIMEOUT = 30
NOT_FOUND_STATUS = 404


def metadata_url(repository, package, version):
    """Составить URL заданного пакета и точной версии."""
    name = quote(package, safe="")
    release = quote(version, safe="")
    return repository.rstrip("/") + "/" + name + "/" + release


def fetch_metadata(package, version, repository):
    """Скачать JSON без вызова npm или библиотек анализа пакетов."""
    url = metadata_url(repository, package, version)
    request = Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "ku-practice2-v8/0.2",
    })
    try:
        with urlopen(request, timeout=NETWORK_TIMEOUT) as response:
            text = response.read().decode("utf-8")
    except HTTPError as error:
        if error.code == NOT_FOUND_STATUS:
            raise ValueError(f"Пакет {package}@{version} не найден") from error
        raise ValueError(f"Ошибка HTTP {error.code} у реестра") from error
    except URLError as error:
        raise OSError(f"Реестр недоступен: {error.reason}") from error
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError("Ответ реестра не является JSON") from error


def validate_dependencies(dependencies):
    """Проверить объект dependencies и сохранить исходные требования."""
    if not isinstance(dependencies, dict):
        raise ValueError("Поле dependencies должно быть JSON-объектом")
    for name, requirement in dependencies.items():
        if not isinstance(name, str) or not name:
            raise ValueError("Некорректное имя зависимости в ответе реестра")
        if not isinstance(requirement, str):
            raise ValueError("Требование версии должно быть строкой")
    return dict(dependencies)


def validate_metadata(metadata, package, version):
    """Проверить соответствие ответа выбранным имени и версии."""
    if not isinstance(metadata, dict):
        raise ValueError("Метаданные должны быть JSON-объектом")
    if metadata.get("name") != package or metadata.get("version") != version:
        raise ValueError("Ответ реестра не соответствует пакету и версии")
    return validate_dependencies(metadata.get("dependencies", {}))


def direct_dependencies(package, version, repository):
    """Получить прямые зависимости заданной версии пакета."""
    metadata = fetch_metadata(package, version, repository)
    return validate_metadata(metadata, package, version)
