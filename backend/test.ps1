$ErrorActionPreference = 'Stop'
$taskPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    throw '请先按照README创建后端虚拟环境并安装测试依赖'
}
$taskWorkspace = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$taskTestDirectory = Join-Path $taskWorkspace ('tmp/backend-tests-' + [guid]::NewGuid().ToString('N'))
Push-Location $PSScriptRoot
try {
    & $taskPython -m pytest -q --tb=short "--basetemp=$taskTestDirectory"
    $taskExitCode = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $taskExitCode
