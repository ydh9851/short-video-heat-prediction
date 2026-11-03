@echo off
setlocal
cd /d "%~dp0.."

echo ============================================================
echo   Git proxy OFF  [direct connection]
echo ============================================================

git config --global --unset-all http.proxy >nul 2>&1
git config --global --unset-all https.proxy >nul 2>&1
git config --global --unset-all "http.https://github.com.proxy" >nul 2>&1
git config --global --unset-all "https.https://github.com.proxy" >nul 2>&1

echo Global proxy keys removed.
echo.
echo Current proxy keys:
git config --global --get-regexp proxy
if errorlevel 1 echo   (none = direct connection)
echo.
echo Self-check: git ls-remote --heads origin
git ls-remote --heads origin >nul 2>&1
if errorlevel 1 (
  echo   [FAIL] direct connection blocked.
  echo          Enable TUN / global mode in FeiNiao, or run tools\git-proxy-on.cmd
) else (
  echo   [OK] direct connection works
)
endlocal
