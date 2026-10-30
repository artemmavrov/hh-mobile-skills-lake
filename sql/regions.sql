-- Stage 6: three regions compared on variant 9 and on the whole IT market as context.
-- Requires tables target and vacancy_skill (stacks.sql).
SET VARIABLE regions = ['Москва', 'Санкт-Петербург', 'Краснодар'];

CREATE OR REPLACE TABLE region_metrics AS
WITH it AS (
    SELECT
        area.name AS area,
        count(*) AS it_vacancies,
        count(net_salary_rub(salary)) AS it_with_salary,
        round(median(net_salary_rub(salary))) AS it_median
    FROM vacancies
    WHERE list_contains(getvariable('regions'), area.name)
    GROUP BY ALL
),
mobile AS (
    SELECT
        area,
        count(*) AS vacancies,
        count(net_salary_rub(salary)) AS with_salary,
        round(quantile_cont(net_salary_rub(salary), 0.25)) AS q1,
        round(median(net_salary_rub(salary))) AS median,
        round(quantile_cont(net_salary_rub(salary), 0.75)) AS q3,
        round(avg(len(skills)) FILTER (WHERE len(skills) > 0), 1) AS avg_skills,
        round(100.0 * count(*) FILTER (WHERE len(skills) = 0) / count(*)) AS no_skills_pct,
        round(100.0 * count(*) FILTER (WHERE schedule = 'remote') / count(*)) AS remote_pct,
        round(100.0 * count(*) FILTER (WHERE experience IN ('between3And6', 'moreThan6')) / count(*)) AS senior_pct,
        count(*) FILTER (WHERE regexp_matches(name, 'android', 'i')) AS android,
        count(*) FILTER (WHERE regexp_matches(name, '(^|[^a-z])(ios|swift)([^a-z]|$)', 'i')) AS ios,
        count(*) FILTER (WHERE regexp_matches(name, 'flutter|react[ -]?native', 'i')) AS cross_platform
    FROM target
    WHERE list_contains(getvariable('regions'), area)
    GROUP BY ALL
)
SELECT
    m.area,
    it.it_vacancies,
    m.vacancies,
    round(100.0 * m.vacancies / it.it_vacancies, 1) AS share_of_it_pct,
    m.with_salary,
    m.q1,
    m.median,
    m.q3,
    it.it_median,
    round(100 * (m.median / it.it_median - 1)) AS premium_vs_it_pct,
    m.avg_skills,
    m.no_skills_pct,
    m.remote_pct,
    m.senior_pct,
    m.android,
    m.ios,
    m.cross_platform
FROM mobile m
JOIN it USING (area)
ORDER BY m.vacancies DESC;

-- Top skills, pairs and triples per region; share = % of the region's vacancies that list skills.
CREATE OR REPLACE TABLE region_stacks AS
WITH vs AS (
    SELECT t.area, s.vacancy_id, s.skill
    FROM vacancy_skill s
    JOIN target t USING (vacancy_id)
    WHERE list_contains(getvariable('regions'), t.area)
),
with_skills AS (
    SELECT area, count(DISTINCT vacancy_id) AS n FROM vs GROUP BY area
),
stacks AS (
    SELECT area, 1 AS size, skill AS stack FROM vs
    UNION ALL
    SELECT a.area, 2, a.skill || ' + ' || b.skill
    FROM vs a JOIN vs b ON a.vacancy_id = b.vacancy_id AND a.skill < b.skill
    UNION ALL
    SELECT a.area, 3, a.skill || ' + ' || b.skill || ' + ' || c.skill
    FROM vs a
    JOIN vs b ON a.vacancy_id = b.vacancy_id AND a.skill < b.skill
    JOIN vs c ON b.vacancy_id = c.vacancy_id AND b.skill < c.skill
)
SELECT
    s.area,
    s.size,
    row_number() OVER (PARTITION BY s.area, s.size ORDER BY count(*) DESC, s.stack) AS rank,
    s.stack,
    count(*) AS vacancies,
    round(100.0 * count(*) / any_value(w.n)) AS share_pct
FROM stacks s
JOIN with_skills w USING (area)
GROUP BY s.area, s.size, s.stack
QUALIFY rank <= 5
ORDER BY s.area, s.size, rank;
