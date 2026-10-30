-- Raw vacancies straight from the lake, only the fields the analysis needs.
CREATE OR REPLACE VIEW vacancies AS
SELECT *
FROM read_json(
    's3://hh-lake/raw/hh_vacancies.ndjson',
    format = 'newline_delimited',
    columns = {
        vacancy_id: 'VARCHAR',
        name: 'VARCHAR',
        area: 'STRUCT(id VARCHAR, name VARCHAR)',
        professional_roles: 'STRUCT(id VARCHAR, name VARCHAR)[]',
        key_skills: 'VARCHAR[]',
        salary: 'STRUCT("from" VARCHAR, "to" VARCHAR, currency VARCHAR, gross VARCHAR)',
        experience: 'STRUCT(id VARCHAR, name VARCHAR)',
        schedule: 'STRUCT(id VARCHAR, name VARCHAR)'
    }
);
