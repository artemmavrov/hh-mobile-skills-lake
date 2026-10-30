"""Explain the growth of pairs and triples: a vacancy with k skills yields C(k, 2) pairs and C(k, 3) triples."""
import json
from math import comb

from hhlake import config, storage
from hhlake.stacks import STACK_NAMES, STACK_SIZES


def main(engine: str = "mapreduce") -> None:
    body = storage.client().get_object(Bucket=config.BUCKET, Key=f"results/{engine}/summary.json")["Body"].read()
    summary = json.loads(body)
    hist = {int(k): v for k, v in summary["skills_per_vacancy"].items()}

    print(f"{'k skills':>8}{'vacancies':>11}{'C(k,1)':>8}{'C(k,2)':>8}{'C(k,3)':>8}"
          f"{'skills':>9}{'pairs':>9}{'triples':>9}")
    totals = dict.fromkeys(STACK_SIZES, 0)
    for k in sorted(hist):
        n = hist[k]
        row = {size: n * comb(k, size) for size in STACK_SIZES}
        for size in STACK_SIZES:
            totals[size] += row[size]
        print(f"{k:>8}{n:>11}{comb(k, 1):>8}{comb(k, 2):>8}{comb(k, 3):>8}{row[1]:>9}{row[2]:>9}{row[3]:>9}")
    print(f"{'total':>8}{sum(hist.values()):>11}{'':>24}{totals[1]:>9}{totals[2]:>9}{totals[3]:>9}")
    for size in STACK_SIZES:
        name = STACK_NAMES[size]
        occurrences, distinct = summary["occurrences"][name], summary["distinct"][name]
        print(f"{name:<8} sum C(k,{size}) = {totals[size]:>5}  MapReduce occurrences = {occurrences:>5}  "
              f"distinct = {distinct:>5}  avg vacancies per distinct = {occurrences / distinct:.2f}")


if __name__ == "__main__":
    main()
