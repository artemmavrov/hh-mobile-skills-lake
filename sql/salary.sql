-- Salary impact of skill pairs and triples inside variant 9.
-- Requires tables target, stack_skills, stack_pairs (stacks.sql).
CREATE OR REPLACE TABLE salaried AS
SELECT vacancy_id, area, experience, skills, net_salary_rub(salary) AS salary
FROM target
WHERE net_salary_rub(salary) IS NOT NULL;

CREATE OR REPLACE TABLE salaried_skill AS
SELECT vacancy_id, salary, unnest(skills) AS skill FROM salaried;

CREATE OR REPLACE TABLE salary_overview AS
SELECT
    (SELECT count(*) FROM target) AS vacancies,
    count(*) AS with_salary,
    count(*) FILTER (WHERE len(skills) > 0) AS with_salary_and_skills,
    round(quantile_cont(salary, 0.25)) AS q1,
    round(median(salary)) AS median,
    round(quantile_cont(salary, 0.75)) AS q3
FROM salaried;

-- Salary level vs skill set: vacancies at or above the median salary against those below it.
CREATE OR REPLACE TABLE salary_bands AS
WITH banded AS (
    SELECT *, CASE WHEN salary >= (SELECT median(salary) FROM salaried) THEN 'high' ELSE 'low' END AS band
    FROM salaried
)
SELECT
    band,
    count(*) AS vacancies,
    round(median(salary)) AS median_salary,
    round(avg(len(skills)), 1) AS avg_skills,
    count(*) FILTER (WHERE len(skills) = 0) AS without_skills
FROM banded
GROUP BY band
ORDER BY band;

CREATE OR REPLACE TABLE salary_band_skills AS
WITH banded AS (
    SELECT s.skill, CASE WHEN s.salary >= (SELECT median(salary) FROM salaried) THEN 'high' ELSE 'low' END AS band
    FROM salaried_skill s
),
sizes AS (
    SELECT
        count(*) FILTER (WHERE salary >= (SELECT median(salary) FROM salaried)) AS high_n,
        count(*) FILTER (WHERE salary < (SELECT median(salary) FROM salaried)) AS low_n
    FROM salaried
)
SELECT
    skill,
    count(*) FILTER (WHERE band = 'high') AS high,
    count(*) FILTER (WHERE band = 'low') AS low,
    round(100.0 * count(*) FILTER (WHERE band = 'high') / any_value(sizes.high_n)) AS high_pct,
    round(100.0 * count(*) FILTER (WHERE band = 'low') / any_value(sizes.low_n)) AS low_pct
FROM banded, sizes
GROUP BY skill
HAVING count(*) >= 3
ORDER BY high_pct - low_pct DESC, skill;

-- Median salary of every skill, pair and triple seen in at least min_support salaried vacancies.
SET VARIABLE min_support = 3;

CREATE OR REPLACE TABLE salary_skill AS
SELECT skill, count(*) AS n, median(salary) AS median_salary
FROM salaried_skill
GROUP BY skill;

CREATE OR REPLACE TABLE salary_pair AS
SELECT a.skill AS skill_1, b.skill AS skill_2, count(*) AS n, median(a.salary) AS median_salary
FROM salaried_skill a
JOIN salaried_skill b ON a.vacancy_id = b.vacancy_id AND a.skill < b.skill
GROUP BY ALL;

CREATE OR REPLACE TABLE salary_triple AS
SELECT a.skill AS skill_1, b.skill AS skill_2, c.skill AS skill_3, count(*) AS n, median(a.salary) AS median_salary
FROM salaried_skill a
JOIN salaried_skill b ON a.vacancy_id = b.vacancy_id AND a.skill < b.skill
JOIN salaried_skill c ON b.vacancy_id = c.vacancy_id AND b.skill < c.skill
GROUP BY ALL
HAVING count(*) >= getvariable('min_support');

-- Pair uplift: median of the pair minus median of its more frequent skill (the base), i.e. the
-- effect of adding the rarer skill to the common one. Frequency is taken over all variant vacancies.
CREATE OR REPLACE TABLE pair_uplift AS
WITH ranked AS (
    SELECT
        p.*,
        f1.vacancies AS freq_1,
        f2.vacancies AS freq_2,
        CASE WHEN f1.vacancies >= f2.vacancies THEN p.skill_1 ELSE p.skill_2 END AS base,
        CASE WHEN f1.vacancies >= f2.vacancies THEN p.skill_2 ELSE p.skill_1 END AS added
    FROM salary_pair p
    JOIN stack_skills f1 ON f1.skill_1 = p.skill_1
    JOIN stack_skills f2 ON f2.skill_1 = p.skill_2
    WHERE p.n >= getvariable('min_support')
)
SELECT
    r.base,
    greatest(r.freq_1, r.freq_2) AS base_freq,
    b.n AS base_n,
    round(b.median_salary) AS base_median,
    r.added,
    r.n AS pair_n,
    round(r.median_salary) AS pair_median,
    round(r.median_salary - b.median_salary) AS uplift,
    round(100 * (r.median_salary / b.median_salary - 1), 1) AS uplift_pct
FROM ranked r
JOIN salary_skill b ON b.skill = r.base
ORDER BY uplift DESC, r.base, r.added;

-- Triple uplift: median of the triple minus median of its most frequent pair (the base pair),
-- i.e. the effect of adding the third skill to the common pair.
CREATE OR REPLACE TABLE triple_uplift AS
WITH sub_pairs AS (
    SELECT t.skill_1, t.skill_2, t.skill_3, sp.pair_1, sp.pair_2, sp.added
    FROM salary_triple t,
    LATERAL (VALUES
        (t.skill_1, t.skill_2, t.skill_3),
        (t.skill_1, t.skill_3, t.skill_2),
        (t.skill_2, t.skill_3, t.skill_1)
    ) AS sp(pair_1, pair_2, added)
),
base_pair AS (
    SELECT s.*, f.vacancies AS base_freq
    FROM sub_pairs s
    JOIN stack_pairs f ON f.skill_1 = s.pair_1 AND f.skill_2 = s.pair_2
    QUALIFY row_number() OVER (
        PARTITION BY s.skill_1, s.skill_2, s.skill_3
        ORDER BY f.vacancies DESC, s.pair_1, s.pair_2
    ) = 1
)
SELECT
    bp.pair_1 || ' + ' || bp.pair_2 AS base,
    bp.base_freq,
    p.n AS base_n,
    round(p.median_salary) AS base_median,
    bp.added,
    t.n AS triple_n,
    round(t.median_salary) AS triple_median,
    round(t.median_salary - p.median_salary) AS uplift,
    round(100 * (t.median_salary / p.median_salary - 1), 1) AS uplift_pct
FROM base_pair bp
JOIN salary_triple t USING (skill_1, skill_2, skill_3)
JOIN salary_pair p ON p.skill_1 = bp.pair_1 AND p.skill_2 = bp.pair_2
ORDER BY uplift DESC, base, bp.added;

-- Final verdict per added skill across all pairs and triples, with the seniority mix of the
-- salaried vacancies that list it (moreThan3 = experience of 3+ years required).
CREATE OR REPLACE TABLE skill_effect AS
WITH effects AS (
    SELECT added, uplift FROM pair_uplift
    UNION ALL
    SELECT added, uplift FROM triple_uplift
),
seniority AS (
    SELECT
        skill,
        round(100.0 * count(*) FILTER (WHERE experience IN ('between3And6', 'moreThan6')) / count(*)) AS senior_pct
    FROM salaried_skill
    JOIN salaried USING (vacancy_id, salary)
    GROUP BY skill
)
SELECT
    e.added AS skill,
    count(*) AS stacks,
    round(median(e.uplift)) AS median_uplift,
    min(e.uplift) AS min_uplift,
    max(e.uplift) AS max_uplift,
    s.n AS salaried_n,
    round(s.median_salary) AS skill_median,
    se.senior_pct,
    CASE WHEN median(e.uplift) > 0 THEN 'raises' WHEN median(e.uplift) < 0 THEN 'lowers' ELSE 'neutral' END AS effect
FROM effects e
JOIN salary_skill s ON s.skill = e.added
JOIN seniority se ON se.skill = e.added
GROUP BY ALL
ORDER BY median_uplift DESC, skill;
