"""Count skills, skill pairs and skill triples of variant 9 with DuckDB reading the same S3 object."""
import argparse
import json
import time

from hhlake import config, db, storage
from hhlake.stacks import STACK_NAMES, STACK_SIZES, header, result_key


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--threads", type=int)
    parser.add_argument("--source", choices=tuple(db.SOURCES), default="raw")
    parser.add_argument("--engine-name", default="duckdb")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    t0 = time.perf_counter()
    con = db.connect(args.threads)
    db.open_vacancies(con, args.source)
    db.run_script(con, "target.sql")
    db.run_script(con, "stacks.sql")
    vacancies = con.execute("SELECT count(*) FROM target").fetchone()[0]
    stacks = {size: con.execute(f"SELECT * FROM stack_{STACK_NAMES[size]}").fetchall() for size in STACK_SIZES}
    t_compute = time.perf_counter()

    summary = {"vacancies": vacancies, "distinct": {}, "occurrences": {}}
    for size, rows in stacks.items():
        name = STACK_NAMES[size]
        storage.put_csv(result_key(args.engine_name, size), header(size), rows)
        summary["distinct"][name] = len(rows)
        summary["occurrences"][name] = sum(r[-1] for r in rows)
    summary["compute_ms"] = round((t_compute - t0) * 1000)
    summary["total_ms"] = round((time.perf_counter() - t0) * 1000)
    storage.client().put_object(Bucket=config.BUCKET, Key=f"results/{args.engine_name}/summary.json",
                                Body=json.dumps(summary, ensure_ascii=False, indent=2).encode("utf-8"))
    if args.quiet:
        print(f"compute_ms={summary['compute_ms']}")
        return
    version = con.execute("SELECT version()").fetchone()[0]
    print(f"duckdb {version}, source {args.source}, compute {summary['compute_ms']} ms, total {summary['total_ms']} ms")
    print(f"variant vacancies: {summary['vacancies']}")
    for size in STACK_SIZES:
        name = STACK_NAMES[size]
        top = ", ".join(f"{' + '.join(r[:-1])}={r[-1]}" for r in stacks[size][:3])
        print(f"{name:8} distinct={summary['distinct'][name]:6} occurrences={summary['occurrences'][name]:6}  top: {top}")
    print(f"saved to s3://{config.BUCKET}/results/{args.engine_name}/")


if __name__ == "__main__":
    main()
