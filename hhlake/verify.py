"""Compare the MapReduce and DuckDB results stored in the lake row by row."""
import json
import sys

from hhlake import config, storage
from hhlake.stacks import STACK_NAMES, STACK_SIZES, result_key


def load(engine: str, size: int) -> dict[tuple, int]:
    rows = storage.get_csv(result_key(engine, size))
    return {tuple(r[f"skill_{i}"] for i in range(1, size + 1)): int(r["vacancies"]) for r in rows}


def summary(engine: str) -> dict:
    body = storage.client().get_object(Bucket=config.BUCKET, Key=f"results/{engine}/summary.json")["Body"].read()
    return json.loads(body)


def main(left: str = "mapreduce", right: str = "duckdb") -> int:
    ok = True
    vac_l, vac_r = summary(left)["vacancies"], summary(right)["vacancies"]
    ok &= vac_l == vac_r
    print(f"{'check':<22}{left:>12}{right:>12}  status")
    print(f"{'variant vacancies':<22}{vac_l:>12}{vac_r:>12}  {'OK' if vac_l == vac_r else 'DIFF'}")
    for size in STACK_SIZES:
        a, b = load(left, size), load(right, size)
        name = STACK_NAMES[size]
        diff = {k for k in a.keys() | b.keys() if a.get(k) != b.get(k)}
        ok &= not diff
        for label, x, y in ((f"{name}: distinct", len(a), len(b)),
                            (f"{name}: occurrences", sum(a.values()), sum(b.values()))):
            print(f"{label:<22}{x:>12}{y:>12}  {'OK' if x == y else 'DIFF'}")
        print(f"{name + ': rows differ':<22}{len(diff):>24}  {'OK' if not diff else 'DIFF'}")
        for k in sorted(diff)[:5]:
            print(f"    {' + '.join(k)}: {a.get(k)} vs {b.get(k)}")
    print("RESULT:", "results are identical" if ok else "results differ")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
