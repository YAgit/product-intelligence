Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$processes = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -like "*uvicorn app.main:app --host 127.0.0.1 --port 8000*"
}

if ($processes) {
    $processes | ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force
    }
}
