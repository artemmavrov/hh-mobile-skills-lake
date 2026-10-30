# Checks that every profiled configuration produced exactly the reference DuckDB result.
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
Set-Location $root
foreach ($engine in "mr_v1", "mr_v2", "mr_v3", "mr_v4", "mr_v5", "duckdb_v1", "duckdb_v2") {
  $verdict = & $python -X utf8 -m hhlake.verify "profile/$engine" duckdb | Select-Object -Last 1
  "{0,-20} {1}" -f "profile/$engine", $verdict
}
