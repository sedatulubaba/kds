param([switch]$WithVision)
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$runtimeDirectory = Join-Path $projectRoot '.runtime'
New-Item -ItemType Directory -Path $runtimeDirectory -Force | Out-Null

$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    $pythonPath = Join-Path $env:LOCALAPPDATA 'Codex\kds-python-3.13.7\python.exe'
}
if (-not (Test-Path -LiteralPath $pythonPath)) {
    $pythonPath = (Get-Command python -ErrorAction Stop).Source
}
$nodeCommand = Get-Command node -ErrorAction SilentlyContinue
$nodePath = if ($nodeCommand) { $nodeCommand.Source } else { 'C:\Program Files\nodejs\node.exe' }
if (-not (Test-Path -LiteralPath $nodePath)) { throw 'Node.js gerekli.' }
$nextPath = Join-Path $projectRoot 'frontend\node_modules\next\dist\bin\next'
if (-not (Test-Path -LiteralPath $nextPath)) { throw 'Önce frontend klasöründe npm ci çalıştırın.' }

function Start-ServiceProcess($name, $executable, $arguments, $directory, $port) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        Write-Output "$name için $port portu kullanımda; yeni süreç başlatılmadı."
        return
    }
    $process = Start-Process -FilePath $executable -ArgumentList ($arguments -join ' ') -WorkingDirectory $directory -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimeDirectory "$name.out.log") -RedirectStandardError (Join-Path $runtimeDirectory "$name.err.log")
    Write-Output "$name başlatıldı (PID $($process.Id), port $port)."
}

Start-ServiceProcess 'backend' $pythonPath @('-B','-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','8000') $projectRoot 8000
if ($WithVision) {
    Start-ServiceProcess 'vision' $pythonPath @('-B','-m','uvicorn','main:app','--app-dir','vision_service','--host','127.0.0.1','--port','8001','--workers','1') $projectRoot 8001
}
Start-ServiceProcess 'frontend' $nodePath @(('"'+$nextPath+'"'),'dev','--hostname','127.0.0.1','--port','3000') (Join-Path $projectRoot 'frontend') 3000
Write-Output 'Arayüz: http://127.0.0.1:3000 (ilk derleme birkaç saniye sürebilir).'
