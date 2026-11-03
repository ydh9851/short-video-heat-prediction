@echo off
rem ============================================================================
rem  short-video-heat-prediction - Python inference service (optional)
rem
rem  Starts the FastAPI sidecar on 127.0.0.1:8100 and warms up the main model.
rem  Backend is configured with system.python.serviceUrl=http://127.0.0.1:8100,
rem  so it will use this service first and fall back to the CLI channel when
rem  the service is down (30s circuit-breaker window).
rem
rem  Log file: data\logs\engine.log
rem ============================================================================
setlocal
cd /d "%~dp0"

echo ============================================================
echo  Python inference service  (127.0.0.1:8100)
echo ============================================================

echo.
echo [1/3] Stopping any process already listening on 8100 ...
for /f "delims=" %%p in ('powershell -NoProfile -Command "$c = Get-NetTCPConnection -LocalPort 8100 -State Listen -ErrorAction SilentlyContinue ^| Select-Object -First 1; if ($c) { $c.OwningProcess }"') do (
  echo   Found PID=%%p - terminating ...
  taskkill /PID %%p /F >nul 2>&1
)
timeout /t 1 >nul

echo.
echo [2/3] Starting uvicorn in background (log: data\logs\engine.log) ...
start "" /MIN cmd /c ".venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8100 --app-dir algorithm\service 1> data\logs\engine.log 2>&1"

echo.
echo [3/3] Waiting for health check (max ~90s, first start warms the model) ...
set "UP=0"
for /L %%i in (1,1,30) do (
  powershell -NoProfile -Command "try { $r = Invoke-RestMethod -Uri 'http://127.0.0.1:8100/health' -TimeoutSec 3; Write-Host ('  health = ' + $r.status + '  featureVersion=' + $r.featureVersion + '  loaded=' + ($r.loadedModels -join ',')); exit 0 } catch { exit 1 }" >nul 2>&1
  if not errorlevel 1 (
    set "UP=1"
    goto :done
  )
  timeout /t 3 >nul
)

:done
if "%UP%"=="0" (
  echo   [FAIL] service did not become healthy. Last 20 lines of data\logs\engine.log:
  powershell -NoProfile -Command "if (Test-Path 'data\logs\engine.log') { Get-Content 'data\logs\engine.log' -Tail 20 }"
) else (
  powershell -NoProfile -Command "try { $r = Invoke-RestMethod -Uri 'http://127.0.0.1:8100/health' -TimeoutSec 3; Write-Host ('  health = ' + $r.status + '  featureVersion=' + $r.featureVersion + '  loaded=' + ($r.loadedModels -join ',')) } catch {}"
)

echo.
echo ------------------------------------------------------------
echo  Done. Check status:  http://localhost:8000/api/predict/engine
echo  Backend falls back to CLI automatically when this is down.
echo ------------------------------------------------------------
endlocal
