import os

ENDPOINT = os.getenv("S3_ENDPOINT", "http://localhost:9100")
ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "rustfsadmin")
SECRET_KEY = os.getenv("S3_SECRET_KEY", "rustfsadmin")
REGION = "us-east-1"

BUCKET = "hh-lake"
RAW_KEY = "raw/hh_vacancies.ndjson"
RESULTS_PREFIX = "results"
