"""Собственный HTTP-клиент метаданных npm."""

import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

NETWORK_TIMEOUT = 30
NOT_FOUND_STATUS = 404


def metadata_url(repository, package, version):
    """Составить URL заданного пакета и точной версии."""
    return (repository.rstrip("/") + "/" + quote(package, safe="")
            + "/" + quote(version, safe=""))


def fetch_json(url, description):
    """Прочитать JSON по HTTP(S) и объяснить ошибки."""
    request = Request(url, headers={
        "Accept": "application/json", "User-Agent": "ku-practice2-v8/0.3",
    })
    try:
        with urlopen(request, timeout=NETWORK_TIMEOUT) as response:
            text = response.read().decode("utf-8")
    except HTTPError as error:
        if error.code == NOT_FOUND_STATUS:
            raise ValueError(f"Пакет {description} не найден") from error
        raise ValueError(f"Ошибка HTTP {error.code} у реестра") from error
    except URLError as error:
        raise OSError(f"Реестр недоступен: {error.reason}") from error
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError("Ответ реестра не является JSON") from error


def fetch_metadata(package, version, repository):
    """Загрузить запись одной точно заданной версии."""
    url = metadata_url(repository, package, version)
    return fetch_json(url, f"{package}@{version}")


def fetch_catalog(package, repository):
    """Загрузить каталог версий без вызова npm."""
    url = repository.rstrip("/") + "/" + quote(package, safe="")
    return fetch_json(url, package)


def validate_dependencies(dependencies):
    """Проверить объект dependencies и исходные требования."""
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
    """Получить прямые требования для отдельной проверки."""
    return validate_metadata(fetch_metadata(package, version, repository),
                             package, version)
