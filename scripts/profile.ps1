# Profiles every configuration (time and peak memory of the whole process tree) and prints a summary.
param([int]$Runs = 5)

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
$out = Join-Path $root "results\profile.csv"
Set-Location $root
Remove-Item $out -ErrorAction SilentlyContinue

$cases = [ordered]@{
  "mr_v1_baseline"   = "hhlake.mr_skills --quiet --engine-name profile/mr_v1"
  "mr_v2_streaming"  = "hhlake.mr_skills --quiet --engine-name profile/mr_v2 --streaming"
  "mr_v3_threads"    = "hhlake.mr_skills --quiet --engine-name profile/mr_v3 --streaming --executor thread --workers 8 --chunk-mb 4"
  "mr_v4_prefilter"  = "hhlake.mr_skills --quiet --engine-name profile/mr_v4 --streaming --executor thread --workers 8 --chunk-mb 4 --prefilter"
  "mr_v5_curated"    = "hhlake.mr_skills --quiet --engine-name profile/mr_v5 --streaming --executor thread --workers 8 --chunk-mb 1 --prefilter --input-key curated/vacancies.ndjson"
  "duckdb_v1_raw"    = "hhlake.duckdb_skills --quiet --engine-name profile/duckdb_v1"
  "duckdb_v2_parquet" = "hhlake.duckdb_skills --quiet --engine-name profile/duckdb_v2 --source curated"
}

foreach ($name in $cases.Keys) {
  & $python -X utf8 -m hhlake.profiler --name $name --runs $Runs --out $out $cases[$name]
}
& $python -X utf8 -m hhlake.profile_report $out
