"""Variant 9: software developers for mobile platforms."""
import re

DEVELOPER_ROLES = frozenset({"96", "104"})  # "Программист, разработчик", "Руководитель группы разработки"

MOBILE_TITLE = re.compile(
    r"android|mobile|мобильн|flutter|react[ -]?native|kotlin multiplatform"
    r"|(?<![a-z])(?:ios|swift|kmp)(?![a-z])",
    re.IGNORECASE,
)
EXCLUDED_TITLE = re.compile(
    r"тестир|аналитик|analyst|дизайн|design|автомобил|менеджер|manager|руководитель проект|преподава|sdet|in test"
    r"|(?<![a-z])qa(?![a-z])",
    re.IGNORECASE,
)


def is_target(vacancy: dict) -> bool:
    title = vacancy.get("name") or ""
    roles = {role["id"] for role in vacancy.get("professional_roles") or []}
    return (
        MOBILE_TITLE.search(title) is not None
        and EXCLUDED_TITLE.search(title) is None
        and not roles.isdisjoint(DEVELOPER_ROLES)
    )


def normalize_skills(skills: list[str] | None) -> list[str]:
    """Lower-cased, de-duplicated, sorted skills of one vacancy."""
    return sorted({s.strip().lower() for s in skills or [] if s.strip()})
