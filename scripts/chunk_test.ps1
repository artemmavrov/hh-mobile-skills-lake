# Runs the MapReduce job with several chunk sizes and checks every result against DuckDB.
param([string]$ChunkMb = "0.5,2,32")

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
Set-Location $root
foreach ($chunk in $ChunkMb -split ",") {
  & $python -X utf8 -m hhlake.mr_skills --chunk-mb $chunk --engine-name mapreduce_chunk_test | Select-Object -First 2
  & $python -X utf8 -m hhlake.verify mapreduce_chunk_test duckdb | Select-Object -Last 1
}
& (Join-Path $PSScriptRoot "s3.ps1") s3 rm s3://hh-lake/results/mapreduce_chunk_test/ --recursive --only-show-errors
