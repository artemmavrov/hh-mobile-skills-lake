"""Pack the raw hh.ru vacancy JSON files into one NDJSON object and upload it to the lake."""
import argparse
import hashlib
import json
from pathlib import Path

from hhlake import config, storage


def build_ndjson(src: Path, out: Path) -> int:
    files = sorted(src.glob("*.json"))
    with out.open("w", encoding="utf-8", newline="\n") as dst:
        for path in files:
            record = json.loads(path.read_text(encoding="utf-8"))
            dst.write(json.dumps(record, ensure_ascii=False) + "\n")
    return len(files)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", type=Path, default=Path("data/hh"))
    parser.add_argument("--out", type=Path, default=Path("data/hh_vacancies.ndjson"))
    args = parser.parse_args()

    count = build_ndjson(args.src, args.out)
    size = args.out.stat().st_size
    md5 = hashlib.md5(args.out.read_bytes()).hexdigest()
    print(f"built {args.out}: {count} vacancies, {size} bytes, md5 {md5}")

    s3 = storage.client()
    if config.BUCKET not in {b["Name"] for b in s3.list_buckets()["Buckets"]}:
        s3.create_bucket(Bucket=config.BUCKET)
        print(f"created bucket {config.BUCKET}")
    s3.upload_file(str(args.out), config.BUCKET, config.RAW_KEY)

    head = s3.head_object(Bucket=config.BUCKET, Key=config.RAW_KEY)
    print(f"uploaded s3://{config.BUCKET}/{config.RAW_KEY}: {head['ContentLength']} bytes, etag {head['ETag']}")


if __name__ == "__main__":
    main()
