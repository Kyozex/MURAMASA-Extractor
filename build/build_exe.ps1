$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

python build\build_icon.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python -m PyInstaller --noconfirm --clean --distpath dist --workpath build\pyinstaller build\MURAMASA.spec
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Built: $projectRoot\dist\MURAMASA-Extractor.exe"
