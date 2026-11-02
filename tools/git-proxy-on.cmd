@echo off
setlocal
cd /d "%~dp0.."

set "PROXY=http://127.0.0.1:7890"

echo ============================================================
echo   Git proxy ON   [FeiNiao VPN 127.0.0.1:7890]
echo ============================================================

powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 7890 -State Listen -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }"
if errorlevel 1 (
  echo   [WARN] port 7890 is not listening - start FeiNiao with system proxy mode
) else (
  echo   port 7890 is listening
)

git config --global http.proxy  %PROXY%
git config --global https.proxy %PROXY%

echo.
echo Written: http.proxy / https.proxy = %PROXY%
echo.
echo Self-check: git ls-remote --heads origin
git ls-remote --heads origin >nul 2>&1
if errorlevel 1 (
  echo   [FAIL] cannot reach origin - check VPN status
) else (
  echo   [OK] fetch / pull / push available
)
endlocal
