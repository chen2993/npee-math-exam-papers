[CmdletBinding()]
param(
  [int]$WebPort = 5173,
  [int]$ApiPort = 8766,
  [string]$Bind = '127.0.0.1',
  [switch]$NoBrowser
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$RepositoryRoot = [System.IO.Path]::GetFullPath($PSScriptRoot)
try { $Python = Get-Command python -ErrorAction Stop }
catch {
  Write-Host '[NPEE 错误] 未找到 Python 3.10+。'
  Write-Host '下载：https://www.python.org/downloads/'
  exit 1
}

Push-Location $RepositoryRoot
try {
  $Arguments = @('-u', '-m', 'npee_math_papers', '--host', $Bind, '--web-port', $WebPort, '--api-port', $ApiPort)
  if ($NoBrowser) { $Arguments += '--no-browser' }
  & $Python.Source @Arguments
  if ($LASTEXITCODE -ne 0) { throw "NPEE 服务退出，退出码 $LASTEXITCODE。" }
}
finally { Pop-Location }
