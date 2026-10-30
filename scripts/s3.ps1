# Runs AWS CLI in a container against the lab RustFS endpoint.
# Usage: .\scripts\s3.ps1 s3 ls s3://hh-lake/ --recursive
$labRoot = Split-Path -Parent $PSScriptRoot
docker run --rm --network lab3_default `
  -e AWS_ACCESS_KEY_ID=rustfsadmin `
  -e AWS_SECRET_ACCESS_KEY=rustfsadmin `
  -e AWS_DEFAULT_REGION=us-east-1 `
  -e AWS_PAGER= `
  -v "${labRoot}:/work" -w /work `
  amazon/aws-cli:2.39.2 --endpoint-url http://rustfs:9000 @args
