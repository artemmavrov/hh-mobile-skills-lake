-- Curated columnar copy of the raw vacancies (see curate.sql), same columns as vacancies.sql.
CREATE OR REPLACE VIEW vacancies AS
SELECT * FROM read_parquet('s3://hh-lake/curated/vacancies.parquet');
