"""A small MapReduce engine that reads an S3 object in byte-range chunks.

Each map task owns the lines that start inside its byte range [start, end):
it skips the partial first line (owned by the previous split) and reads past
`end` to finish its last line, as Hadoop's LineRecordReader does.
"""
import sys
import time
import zlib
from collections import Counter, defaultdict
from concurrent.futures import FIRST_COMPLETED, Executor, ProcessPoolExecutor, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from typing import Callable, Hashable, Iterable, Iterator

from hhlake import storage

TAIL_STEP = 64 * 1024
STREAM_STEP = 64 * 1024
TAIL_STEP_MIN = 16 * 1024

Mapper = Callable[[bytes], Iterable[tuple[Hashable, int]]]
EXECUTORS = {"process": ProcessPoolExecutor, "thread": ThreadPoolExecutor}


@dataclass(frozen=True)
class Split:
    index: int
    start: int
    end: int


@dataclass
class MapOutput:
    split: int
    partitions: list
    stats: Counter = field(default_factory=Counter)


class InjectedMapperFailure(RuntimeError):
    pass


def plan_splits(size: int, chunk_size: int) -> list[Split]:
    return [Split(i, start, min(start + chunk_size, size)) for i, start in enumerate(range(0, size, chunk_size))]


def iter_lines_buffered(bucket: str, key: str, size: int, split: Split, stats: Counter) -> Iterator[bytes]:
    """Download the whole split into memory, then extend it in TAIL_STEP pieces up to the next newline."""
    lo = split.start - 1 if split.start else 0
    buf = storage.read_range(bucket, key, lo, split.end)
    stats["bytes_read"] += len(buf)
    if split.start:
        newline = buf.find(b"\n")
        if newline < 0:
            return
        buf = buf[newline + 1:]
    if not buf:
        return
    pos = split.end
    while not buf.endswith(b"\n") and pos < size:
        more = storage.read_range(bucket, key, pos, min(pos + TAIL_STEP, size))
        stats["bytes_read"] += len(more)
        pos += len(more)
        newline = more.find(b"\n")
        if newline >= 0:
            buf += more[:newline + 1]
            break
        buf += more
    for line in buf.split(b"\n"):
        if line:
            yield line


def iter_lines_streaming(bucket: str, key: str, size: int, split: Split, stats: Counter) -> Iterator[bytes]:
    """Stream the split range piece by piece and finish the last line with small, doubling tail reads."""
    lo = split.start - 1 if split.start else 0
    body = storage.open_range(bucket, key, lo, split.end)
    skip_first = split.start > 0
    tail = b""
    try:
        for piece in body.iter_chunks(STREAM_STEP):
            stats["bytes_read"] += len(piece)
            lines = (tail + piece).split(b"\n")
            tail = lines.pop()
            for line in lines:
                if skip_first:
                    skip_first = False
                elif line:
                    yield line
    finally:
        body.close()
    if skip_first or not tail:
        return
    pos, step = split.end, TAIL_STEP_MIN
    while pos < size:
        more = storage.read_range(bucket, key, pos, min(pos + step, size))
        stats["bytes_read"] += len(more)
        pos += len(more)
        newline = more.find(b"\n")
        if newline >= 0:
            tail += more[:newline]
            break
        tail += more
        step *= 2
    yield tail


def partition_of(key: Hashable, reducers: int) -> int:
    return zlib.crc32(repr(key).encode("utf-8")) % reducers


def map_task(mapper: Mapper, bucket: str, key: str, size: int, split: Split,
             reducers: int, combine: bool, streaming: bool, fail: bool) -> MapOutput:
    stats = Counter()
    partitions = [Counter() if combine else [] for _ in range(reducers)]
    fail_at = (split.end - split.start) // 2 if fail else -1
    reader = iter_lines_streaming if streaming else iter_lines_buffered
    consumed = 0
    for line in reader(bucket, key, size, split, stats):
        consumed += len(line) + 1
        if 0 <= fail_at < consumed:
            raise InjectedMapperFailure(f"map task {split.index} crashed after {stats['lines']} lines")
        stats["lines"] += 1
        for out_key, value in mapper(line):
            stats["map_records"] += 1
            part = partitions[partition_of(out_key, reducers)]
            if combine:
                part[out_key] += value
            else:
                part.append((out_key, value))
    stats["shuffle_records"] = sum(len(p) for p in partitions)
    return MapOutput(split.index, partitions, stats)


def reduce_task(chunks: list) -> dict:
    result = defaultdict(int)
    for chunk in chunks:
        items = chunk.items() if isinstance(chunk, Counter) else chunk
        for out_key, value in items:
            result[out_key] += value
    return dict(result)


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def run_maps(pool: Executor, mapper: Mapper, bucket: str, key: str, size: int, splits: list[Split],
             reducers: int, combine: bool, streaming: bool, fail_splits: set[int],
             max_attempts: int) -> list[MapOutput]:
    attempts = Counter()
    pending = {}

    def submit(split: Split) -> None:
        attempts[split.index] += 1
        inject = split.index in fail_splits and attempts[split.index] == 1
        future = pool.submit(map_task, mapper, bucket, key, size, split, reducers, combine, streaming, inject)
        pending[future] = split

    for split in splits:
        submit(split)
    outputs = []
    while pending:
        done, _ = wait(pending, return_when=FIRST_COMPLETED)
        for future in done:
            split = pending.pop(future)
            try:
                outputs.append(future.result())
            except Exception as exc:
                if attempts[split.index] >= max_attempts:
                    raise
                log(f"[retry] map task {split.index} attempt {attempts[split.index]} failed: {exc}; rescheduling")
                submit(split)
    return sorted(outputs, key=lambda o: o.split)


def run_job(mapper: Mapper, bucket: str, key: str, *, chunk_size: int, workers: int, reducers: int,
            combine: bool = True, streaming: bool = False, executor: str = "process",
            fail_splits: Iterable[int] = (), max_attempts: int = 3) -> tuple[dict, Counter]:
    t0 = time.perf_counter()
    size = storage.object_size(bucket, key)
    splits = plan_splits(size, chunk_size)
    stats = Counter(object_bytes=size, splits=len(splits), reducers=reducers)

    with EXECUTORS[executor](max_workers=workers) as pool:
        outputs = run_maps(pool, mapper, bucket, key, size, splits, reducers, combine, streaming,
                           set(fail_splits), max_attempts)
        t_map = time.perf_counter()
        shuffled = [[out.partitions[r] for out in outputs] for r in range(reducers)]
        for out in outputs:
            stats.update(out.stats)
        reduced = list(pool.map(reduce_task, shuffled))
    t_reduce = time.perf_counter()

    result = {}
    for part in reduced:
        result.update(part)
    stats["map_ms"] = round((t_map - t0) * 1000)
    stats["reduce_ms"] = round((t_reduce - t_map) * 1000)
    return result, stats
