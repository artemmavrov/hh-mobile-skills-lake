"""Build the curated layer: a Parquet file and a narrow NDJSON with only the analysed fields."""
import time

from hhlake import config, db, storage

CURATED_KEYS = ("curated/vacancies.parquet", "curated/vacancies.ndjson")


def main() -> None:
    t0 = time.perf_counter()
    con = db.connect()
    db.open_vacancies(con, "raw")
    db.run_script(con, "curate.sql")
    elapsed = time.perf_counter() - t0
    raw = storage.object_size(config.BUCKET, config.RAW_KEY)
    print(f"curated layer built in {elapsed:.2f} s")
    print(f"{config.RAW_KEY:<28}{raw:>12} bytes")
    for key in CURATED_KEYS:
        size = storage.object_size(config.BUCKET, key)
        print(f"{key:<28}{size:>12} bytes  ({100 * size / raw:.1f}% of raw)")


if __name__ == "__main__":
    main()
