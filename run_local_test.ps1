$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$InputDir = Join-Path $RepoRoot "local_inputs"
$OutputDir = Join-Path $RepoRoot "local_outputs"

New-Item -ItemType Directory -Force -Path $InputDir | Out-Null
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$PdfFiles = @(Get-ChildItem -Path $InputDir -File -Filter "*.pdf")
$ExcelFiles = @(Get-ChildItem -Path $InputDir -File | Where-Object { $_.Extension -in @(".xlsx", ".xlsm") })

if ($PdfFiles.Count -ne 1) {
    Write-Host "Expected exactly one PDF in $InputDir, found $($PdfFiles.Count)." -ForegroundColor Yellow
    Write-Host "Place the real DVM-AE PDF in local_inputs and run again."
    exit 1
}

if ($ExcelFiles.Count -ne 1) {
    Write-Host "Expected exactly one Excel template (.xlsx or .xlsm) in $InputDir, found $($ExcelFiles.Count)." -ForegroundColor Yellow
    Write-Host "Place the corrected EZ FAB FAI template in local_inputs and run again."
    exit 1
}

$PdfPath = $PdfFiles[0].FullName
$TemplatePath = $ExcelFiles[0].FullName

Write-Host "Running EZ FAI local test..." -ForegroundColor Cyan
Write-Host "PDF: $PdfPath"
Write-Host "Template: $TemplatePath"
Write-Host "Output folder: $OutputDir"

python (Join-Path $RepoRoot "local_test_runner.py") --pdf $PdfPath --template $TemplatePath --output-dir $OutputDir

Write-Host ""
Write-Host "Created outputs:" -ForegroundColor Green
Write-Host "  Ballooned PDF: $(Join-Path $OutputDir ($PdfFiles[0].BaseName + '_BALLOONED.pdf'))"
Write-Host "  FAI Excel: $(Join-Path $OutputDir ($PdfFiles[0].BaseName + '_FAI.xlsx'))"
Write-Host "  Debug report: $(Join-Path $OutputDir 'EZ_FAI_DEBUG_REPORT.txt')"
Write-Host "  Extraction summary: $(Join-Path $OutputDir 'EXTRACTION_SUMMARY.txt')"
