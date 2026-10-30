-- Skill stacks of size 1, 2 and 3: one row per vacancy and distinct ordered skill combination.
CREATE OR REPLACE TABLE vacancy_skill AS
SELECT vacancy_id, unnest(skills) AS skill FROM target;

CREATE OR REPLACE TABLE stack_skills AS
SELECT skill AS skill_1, count(*) AS vacancies
FROM vacancy_skill
GROUP BY ALL
ORDER BY vacancies DESC, skill_1;

CREATE OR REPLACE TABLE stack_pairs AS
SELECT a.skill AS skill_1, b.skill AS skill_2, count(*) AS vacancies
FROM vacancy_skill a
JOIN vacancy_skill b ON a.vacancy_id = b.vacancy_id AND a.skill < b.skill
GROUP BY ALL
ORDER BY vacancies DESC, skill_1, skill_2;

CREATE OR REPLACE TABLE stack_triples AS
SELECT a.skill AS skill_1, b.skill AS skill_2, c.skill AS skill_3, count(*) AS vacancies
FROM vacancy_skill a
JOIN vacancy_skill b ON a.vacancy_id = b.vacancy_id AND a.skill < b.skill
JOIN vacancy_skill c ON b.vacancy_id = c.vacancy_id AND b.skill < c.skill
GROUP BY ALL
ORDER BY vacancies DESC, skill_1, skill_2, skill_3;
