import csv
import io
from functools import cache
from urllib.parse import urlparse

import boto3
from botocore.config import Config

from hhlake import config


@cache
def client():
    return boto3.client(
        "s3",
        endpoint_url=config.ENDPOINT,
        aws_access_key_id=config.ACCESS_KEY,
        aws_secret_access_key=config.SECRET_KEY,
        region_name=config.REGION,
        config=Config(
            s3={"addressing_style": "path"},
            retries={"max_attempts": 5, "mode": "standard"},
            max_pool_connections=32,
        ),
    )


def object_size(bucket: str, key: str) -> int:
    return client().head_object(Bucket=bucket, Key=key)["ContentLength"]


def read_range(bucket: str, key: str, start: int, end: int) -> bytes:
    """Read bytes [start, end) of an object."""
    if start >= end:
        return b""
    resp = client().get_object(Bucket=bucket, Key=key, Range=f"bytes={start}-{end - 1}")
    return resp["Body"].read()


def open_range(bucket: str, key: str, start: int, end: int):
    """Open a streaming body for bytes [start, end) of an object."""
    return client().get_object(Bucket=bucket, Key=key, Range=f"bytes={start}-{end - 1}")["Body"]


def put_csv(key: str, header: list[str], rows) -> None:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    client().put_object(Bucket=config.BUCKET, Key=key, Body=buf.getvalue().encode("utf-8"), ContentType="text/csv")


def get_csv(key: str) -> list[dict[str, str]]:
    body = client().get_object(Bucket=config.BUCKET, Key=key)["Body"].read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(body)))


def duckdb_s3_secret() -> str:
    url = urlparse(config.ENDPOINT)
    return f"""
        CREATE OR REPLACE SECRET hh_lake (
            TYPE s3,
            KEY_ID '{config.ACCESS_KEY}',
            SECRET '{config.SECRET_KEY}',
            REGION '{config.REGION}',
            ENDPOINT '{url.netloc}',
            URL_STYLE 'path',
            USE_SSL {str(url.scheme == "https").lower()}
        )
    """
