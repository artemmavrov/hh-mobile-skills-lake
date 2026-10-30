-- Variant 9: developers for mobile platforms.
CREATE OR REPLACE TABLE target AS
SELECT
    vacancy_id,
    name,
    area.name AS area,
    experience.id AS experience,
    schedule.id AS schedule,
    salary,
    list_sort(list_distinct(list_filter(
        list_transform(key_skills, lambda s: lower(trim(s))),
        lambda s: s <> ''
    ))) AS skills
FROM vacancies
WHERE regexp_matches(
        name,
        'android|mobile|мобильн|flutter|react[ -]?native|kotlin multiplatform|(^|[^a-z])(ios|swift|kmp)([^a-z]|$)',
        'i')
  AND NOT regexp_matches(
        name,
        'тестир|аналитик|analyst|дизайн|design|автомобил|менеджер|manager|руководитель проект|преподава|sdet|in test|(^|[^a-z])qa([^a-z]|$)',
        'i')
  AND list_has_any(list_transform(professional_roles, lambda r: r.id), ['96', '104']);
