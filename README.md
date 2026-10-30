# Навыки мобильных разработчиков: MapReduce и DuckDB поверх RustFS

Домашнее задание № 3 по дисциплине «Инженерия данных», вариант 9 — «Программист, разработчик на мобильных платформах».

Отчёт: [report/report.pdf](report/report.pdf).

## Состав

| Путь | Назначение |
|---|---|
| `docker-compose.yml` | RustFS на четырёх папках-дисках, S3 API на `localhost:9100` |
| `hhlake/load_data.py` | упаковка 10 000 JSON-вакансий в NDJSON и загрузка в `s3://hh-lake/raw/` |
| `hhlake/mapreduce.py` | собственный движок MapReduce: чтение объекта из S3 чанками по диапазонам байт, combiner, партиционирование, повтор упавших map-задач |
| `hhlake/mr_skills.py` | навыки, пары и тройки навыков варианта на MapReduce |
| `hhlake/duckdb_skills.py`, `sql/` | то же на DuckDB SQL по тому же объекту |
| `hhlake/verify.py` | построчное сравнение результатов двух движков |
| `hhlake/combinatorics.py` | объяснение роста числа пар и троек через C(k, n) |
| `hhlake/salary.py`, `sql/salary.sql` | влияние пар и троек навыков на медианную зарплату |
| `hhlake/regions.py`, `sql/regions.sql` | сравнение Москвы, Санкт-Петербурга и Краснодара |
| `hhlake/curate.py`, `sql/curate.sql` | curated-слой (Parquet и узкий NDJSON) для оптимизации |
| `hhlake/profiler.py`, `scripts/profile.ps1` | профилирование времени и пиковой памяти дерева процессов |

## Запуск

```powershell
docker compose up -d
uv sync
.venv\Scripts\python -X utf8 -m hhlake.load_data --src data/hh
.venv\Scripts\python -X utf8 -m hhlake.mr_skills
.venv\Scripts\python -X utf8 -m hhlake.duckdb_skills
.venv\Scripts\python -X utf8 -m hhlake.verify
.venv\Scripts\python -X utf8 -m hhlake.salary
.venv\Scripts\python -X utf8 -m hhlake.regions
.venv\Scripts\python -X utf8 -m hhlake.curate
.\scripts\profile.ps1 -Runs 5
```

Исходные JSON-файлы вакансий (`data/hh/`) в репозиторий не входят.
