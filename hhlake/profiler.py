"""Run a command several times and record wall time and peak memory of its whole process tree.

Memory is the peak of the summed RSS (working set on Windows) of the process and all of its
children, sampled every few milliseconds, so worker processes of the MapReduce pool are included.
"""
import argparse
import csv
import re
import shlex
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path

import psutil

MIB = 1024 * 1024


def tree_rss(proc: psutil.Process) -> int:
    total = 0
    for p in [proc, *proc.children(recursive=True)]:
        try:
            total += p.memory_info().rss
        except psutil.Error:
            pass
    return total


def measure(cmd: list[str], interval: float) -> tuple[float, int, int, int | None]:
    start = time.perf_counter()
    child = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
    proc = psutil.Process(child.pid)
    peak = 0
    stop = threading.Event()

    def sample() -> None:
        nonlocal peak
        while not stop.is_set():
            try:
                peak = max(peak, tree_rss(proc))
            except psutil.Error:
                pass
            time.sleep(interval)

    sampler = threading.Thread(target=sample, daemon=True)
    sampler.start()
    output, _ = child.communicate()
    elapsed = time.perf_counter() - start
    stop.set()
    sampler.join()
    match = re.search(r"compute_ms=(\d+)", output)
    return elapsed, peak, child.returncode, int(match.group(1)) if match else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--interval", type=float, default=0.005)
    parser.add_argument("--out", type=Path, default=Path("results/profile.csv"))
    parser.add_argument("command", help="python module and arguments, e.g. 'hhlake.mr_skills --quiet'")
    args = parser.parse_args()

    cmd = [sys.executable, "-X", "utf8", "-m", *shlex.split(args.command)]
    new_file = not args.out.exists()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    times, peaks, computes = [], [], []
    with args.out.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["name", "run", "seconds", "compute_seconds", "peak_mib", "command"])
        for run in range(1, args.runs + 1):
            elapsed, peak, code, compute_ms = measure(cmd, args.interval)
            if code:
                sys.exit(f"{args.name}: run {run} failed with exit code {code}")
            compute = compute_ms / 1000 if compute_ms is not None else float("nan")
            times.append(elapsed)
            computes.append(compute)
            peaks.append(peak / MIB)
            writer.writerow([args.name, run, f"{elapsed:.3f}", f"{compute:.3f}", f"{peak / MIB:.1f}", args.command])
            print(f"{args.name:<20} run {run}: wall {elapsed:6.3f} s  compute {compute:6.3f} s  "
                  f"peak {peak / MIB:7.1f} MiB")
    print(f"{args.name:<20} mean: wall {statistics.mean(times):.3f} s, compute {statistics.mean(computes):.3f} s, "
          f"peak {statistics.mean(peaks):.1f} MiB")


if __name__ == "__main__":
    main()
