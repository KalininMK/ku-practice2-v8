"""Ленивое получение вершин npm с кэшем HTTP-каталогов."""

from .registry import fetch_catalog, validate_metadata
from .semver import select_version


class NpmRepository:
    """Хранить каталоги и выбирать версии объявленных зависимостей."""

    def __init__(self, address, excluded=""):
        """Настроить адрес, фильтр и кэши для одного анализа."""
        self.address = address
        self.excluded = excluded
        self.catalogs = {}
        self.resolved = {}

    def catalog(self, name):
        """Получить каталог одного имени не более одного раза."""
        if name not in self.catalogs:
            metadata = fetch_catalog(name, self.address)
            if not isinstance(metadata, dict) or metadata.get("name") != name:
                raise ValueError(f"Неверный каталог пакета {name}")
            if not isinstance(metadata.get("versions"), dict):
                raise ValueError(f"У пакета {name} нет каталога versions")
            self.catalogs[name] = metadata
        return self.catalogs[name]

    def resolve(self, name, requirement):
        """Найти максимальную допустимую версию или dist-tag."""
        key = name, requirement
        if key not in self.resolved:
            catalog = self.catalog(name)
            tags = catalog.get("dist-tags", {})
            if not isinstance(tags, dict):
                raise ValueError(f"Некорректные dist-tags пакета {name}")
            selected = tags.get(requirement, requirement)
            version = select_version(catalog["versions"], selected)
            self.resolved[key] = name, version
        return self.resolved[key]

    def dependencies(self, node):
        """Получить соседей; исключённые имена не скачивать."""
        name, version = node
        versions = self.catalog(name)["versions"]
        if version not in versions:
            raise ValueError(f"Пакет {name}@{version} не найден")
        requirements = validate_metadata(versions[version], name, version)
        result = []
        for dependency, requirement in sorted(requirements.items()):
            if self.excluded and self.excluded in dependency:
                continue
            result.append(self.resolve(dependency, requirement))
        return result
