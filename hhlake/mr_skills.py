"""Count skills, skill pairs and skill triples of variant 9 with the custom MapReduce engine."""
import argparse
import json
import time
from itertools import combinations

from hhlake import config, mapreduce, storage, variant
from hhlake.stacks import STACK_NAMES, STACK_SIZES, header, ordered, result_key

VACANCY_KEY = ()
ROLE_TOKENS = tuple(f'"{role}"'.encode() for role in sorted(variant.DEVELOPER_ROLES))


def stack_mapper(line: bytes):
    vacancy = json.loads(line)
    if not variant.is_target(vacancy):
        return
    skills = variant.normalize_skills(vacancy.get("key_skills"))
    yield VACANCY_KEY, 1
    yield ("#skills", len(skills)), 1
    for size in STACK_SIZES:
        for stack in combinations(skills, size):
            yield stack, 1


def prefiltered_stack_mapper(line: bytes):
    """Skip JSON parsing of lines that do not even contain a developer role id token."""
    if not any(token in line for token in ROLE_TOKENS):
        return ()
    return stack_mapper(line)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunk-mb", type=float, default=8)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--reducers", type=int, default=4)
    parser.add_argument("--no-combiner", action="store_true")
    parser.add_argument("--executor", choices=("process", "thread"), default="process")
    parser.add_argument("--streaming", action="store_true", help="stream ranges instead of buffering whole splits")
    parser.add_argument("--prefilter", action="store_true", help="skip JSON parsing of lines without a role id")
    parser.add_argument("--input-key", default=config.RAW_KEY)
    parser.add_argument("--fail-split", type=int, action="append", default=[], help="inject a mapper crash")
    parser.add_argument("--engine-name", default="mapreduce")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    t0 = time.perf_counter()
    counts, stats = mapreduce.run_job(
        prefiltered_stack_mapper if args.prefilter else stack_mapper, config.BUCKET, args.input_key,
        chunk_size=int(args.chunk_mb * 1024 * 1024), workers=args.workers, reducers=args.reducers,
        combine=not args.no_combiner, streaming=args.streaming, executor=args.executor,
        fail_splits=args.fail_split,
    )
    compute_ms = round((time.perf_counter() - t0) * 1000)
    by_size = {size: {k: v for k, v in counts.items() if len(k) == size and k[0] != "#skills"} for size in STACK_SIZES}
    skills_hist = {k[1]: v for k, v in counts.items() if len(k) == 2 and k[0] == "#skills"}
    for size in STACK_SIZES:
        storage.put_csv(result_key(args.engine_name, size), header(size),
                        [(*stack, n) for stack, n in ordered(by_size[size])])
    summary = {
        "vacancies": counts.get(VACANCY_KEY, 0),
        "skills_per_vacancy": dict(sorted(skills_hist.items())),
        "distinct": {STACK_NAMES[s]: len(by_size[s]) for s in STACK_SIZES},
        "occurrences": {STACK_NAMES[s]: sum(by_size[s].values()) for s in STACK_SIZES},
        "stats": dict(stats),
        "compute_ms": compute_ms,
        "total_ms": round((time.perf_counter() - t0) * 1000),
    }
    storage.client().put_object(Bucket=config.BUCKET, Key=f"results/{args.engine_name}/summary.json",
                                Body=json.dumps(summary, ensure_ascii=False, indent=2).encode("utf-8"))
    if args.quiet:
        print(f"compute_ms={compute_ms}")
        return
    st = summary["stats"]
    print(f"input  s3://{config.BUCKET}/{args.input_key}: {st['object_bytes']} bytes, "
          f"{st['splits']} splits of {args.chunk_mb:g} MiB, {args.workers} {args.executor} mappers, "
          f"{args.reducers} reducers")
    print(f"map    lines={st['lines']} bytes_read={st['bytes_read']} map_records={st['map_records']} "
          f"shuffle_records={st['shuffle_records']} ({st['map_ms']} ms)")
    print(f"reduce {st['reduce_ms']} ms, compute {compute_ms} ms, total with upload {summary['total_ms']} ms")
    print(f"variant vacancies: {summary['vacancies']}")
    for size in STACK_SIZES:
        name = STACK_NAMES[size]
        top = ", ".join(f"{' + '.join(k)}={v}" for k, v in ordered(by_size[size])[:3])
        print(f"{name:8} distinct={summary['distinct'][name]:6} occurrences={summary['occurrences'][name]:6}  top: {top}")
    print(f"saved to s3://{config.BUCKET}/results/{args.engine_name}/")


if __name__ == "__main__":
    main()
