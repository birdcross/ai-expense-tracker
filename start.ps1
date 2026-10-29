$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Join-Path $PSScriptRoot 'backend')
$venvPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (Test-Path -LiteralPath $venvPython) {
    & $venvPython -c "import fastapi, uvicorn, openai, pydantic" 2>$null
    if ($LASTEXITCODE -ne 0) {
        py -3 -m venv (Join-Path $PSScriptRoot '.venv')
        & $venvPython -m pip install -r requirements.txt
    }
}
if (-not (Test-Path -LiteralPath $venvPython)) {
    py -3 -m venv (Join-Path $PSScriptRoot '.venv')
    & $venvPython -m pip install -r requirements.txt
}
& $venvPython -m uvicorn main:app --host 127.0.0.1 --port 8017
