# Crashes map tasks 2 and 5 on their first attempt and checks the recovered result against DuckDB.
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
Set-Location $root
& $python -X utf8 -m hhlake.mr_skills --fail-split 2 --fail-split 5 --engine-name mapreduce_failover
& $python -X utf8 -m hhlake.verify mapreduce_failover duckdb
