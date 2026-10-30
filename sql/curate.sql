-- One-off ETL from the raw layer: keep only the fields the analysis reads, drop descriptions.
-- Requires the raw view from vacancies.sql.
COPY (SELECT * FROM vacancies ORDER BY vacancy_id)
TO 's3://hh-lake/curated/vacancies.parquet' (FORMAT parquet, COMPRESSION zstd);

COPY (SELECT * FROM vacancies ORDER BY vacancy_id)
TO 's3://hh-lake/curated/vacancies.ndjson' (FORMAT json);
