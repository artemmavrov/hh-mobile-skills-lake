from pathlib import Path

import duckdb

from hhlake import storage

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
SOURCES = {"raw": "vacancies.sql", "curated": "vacancies_curated.sql"}


def connect(threads: int | None = None) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("SET enable_progress_bar = false")
    if threads:
        con.execute(f"SET threads = {threads}")
    con.execute("LOAD httpfs")
    con.execute(storage.duckdb_s3_secret())
    return con


def run_script(con: duckdb.DuckDBPyConnection, name: str) -> None:
    con.execute((SQL_DIR / name).read_text(encoding="utf-8"))


def open_vacancies(con: duckdb.DuckDBPyConnection, source: str = "raw") -> None:
    run_script(con, "macros.sql")
    run_script(con, SOURCES[source])


def show(con: duckdb.DuckDBPyConnection, title: str, query: str, max_rows: int = 40) -> None:
    print(f"== {title}")
    con.sql(query).show(max_rows=max_rows, max_width=200)


def export(con: duckdb.DuckDBPyConnection, table: str, key: str) -> None:
    rel = con.execute(f"SELECT * FROM {table}")
    header = [d[0] for d in rel.description]
    storage.put_csv(key, header, rel.fetchall())
