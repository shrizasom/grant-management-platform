param(
    [string]$MongoUri = "mongodb://localhost:27017",
    [string]$Database = "grants"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$dataPath = Join-Path $root "candidate_packet/data"

$mongoImport = Get-Command mongoimport -ErrorAction SilentlyContinue
if ($mongoImport) {
    $mongoImportPath = $mongoImport.Source
} else {
    $candidates = Get-ChildItem -Path "C:\Program Files\MongoDB", "C:\Program Files (x86)\MongoDB" -Recurse -Filter mongoimport.exe -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending
    if (-not $candidates) {
        throw "mongoimport was not found. Install MongoDB Database Tools, then rerun this script."
    }
    $mongoImportPath = $candidates[0].FullName
}

Write-Host "Using mongoimport at $mongoImportPath"

foreach ($collection in @("programCycles", "applications", "reviewers", "reviews")) {
    & $mongoImportPath --uri $MongoUri --db $Database --collection $collection --drop --file (Join-Path $dataPath "$collection.json")
}
