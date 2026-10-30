"""Summarise results/profile.csv: wall time, compute time and peak memory per configuration."""
import csv
import statistics
import sys
from collections import defaultdict


def main(path: str = "results/profile.csv") -> None:
    runs = defaultdict(list)
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            runs[row["name"]].append((float(row["seconds"]), float(row["compute_seconds"]), float(row["peak_mib"])))
    print(f"{'configuration':<19}{'runs':>5}{'wall s':>8}{'sd':>7}{'compute s':>11}{'sd':>7}{'min':>7}{'max':>7}"
          f"{'peak MiB':>10}{'min':>8}{'max':>8}")
    for name, values in runs.items():
        wall, compute, peak = ([v[i] for v in values] for i in range(3))
        print(f"{name:<19}{len(values):>5}{statistics.mean(wall):>8.3f}{statistics.stdev(wall):>7.3f}"
              f"{statistics.mean(compute):>11.3f}{statistics.stdev(compute):>7.3f}{min(compute):>7.3f}"
              f"{max(compute):>7.3f}{statistics.mean(peak):>10.1f}{min(peak):>8.1f}{max(peak):>8.1f}")


if __name__ == "__main__":
    main(*sys.argv[1:])
