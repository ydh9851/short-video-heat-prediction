@echo off
setlocal
cd /d "%~dp0.."

echo ============================================================
echo   Git proxy status
echo ============================================================

echo [1] global proxy config
git config --global --get-regexp proxy
if errorlevel 1 echo     (none = direct connection)

echo.
echo [2] FeiNiao proxy port 7890
powershell -NoProfile -Command "$c = Get-NetTCPConnection -LocalPort 7890 -State Listen -ErrorAction SilentlyContinue; if ($c) { '    listening, pid ' + $c[0].OwningProcess } else { '    not listening' }"

echo.
echo [3] remote connectivity
git ls-remote --heads origin >nul 2>&1
if errorlevel 1 (
  echo     [FAIL] origin unreachable
  echo     proxy mode : run tools\git-proxy-on.cmd
  echo     direct mode: enable TUN / global mode in FeiNiao
) else (
  echo     [OK] pull / push available
)

echo.
echo [4] note
echo     proxy mode  = FeiNiao 7890
echo     direct mode = no proxy
echo     Leishen accelerator port 10908 is never used
endlocal
