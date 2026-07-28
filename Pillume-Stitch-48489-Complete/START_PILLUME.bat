@echo off
setlocal
chcp 65001 >nul
title Pillume Dashboard + AI Server

for %%I in ("%~dp0.") do set "PROJECT_ROOT=%%~fI"
set "DASHBOARD_URL=http://localhost:3000/dashboard.html"

if not exist "%PROJECT_ROOT%\package.json" (
  echo [오류] package.json을 찾을 수 없습니다.
  echo START_PILLUME.bat 파일을 Pillume 완성 폴더 안에서 실행해 주세요.
  pause
  exit /b 1
)

if not exist "%PROJECT_ROOT%\public" mkdir "%PROJECT_ROOT%\public"
copy /Y "%PROJECT_ROOT%\dashboard.html" "%PROJECT_ROOT%\public\dashboard.html" >nul

powershell.exe -NoProfile -Command "try { $null = Invoke-WebRequest -UseBasicParsing -Uri '%DASHBOARD_URL%' -TimeoutSec 1; exit 0 } catch { exit 1 }"
if not errorlevel 1 (
  echo Pillume 서버가 이미 실행 중입니다.
  start "" "%DASHBOARD_URL%"
  exit /b 0
)

where node >nul 2>&1
if errorlevel 1 (
  echo [오류] Node.js가 설치되어 있지 않습니다.
  echo https://nodejs.org 에서 LTS 버전을 설치한 뒤 다시 실행해 주세요.
  pause
  exit /b 1
)

if not exist "%PROJECT_ROOT%\node_modules" (
  echo 처음 실행이라 필요한 패키지를 설치합니다...
  pushd "%PROJECT_ROOT%"
  call npm install
  if errorlevel 1 (
    popd
    echo [오류] npm install에 실패했습니다.
    pause
    exit /b 1
  )
  popd
)

start "" /b powershell.exe -NoProfile -WindowStyle Hidden -Command "$url='%DASHBOARD_URL%'; for($i=0; $i -lt 40; $i++){ try { $null=Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 1; Start-Process $url; exit } catch { Start-Sleep -Milliseconds 500 } }"

echo Pillume 서버를 시작합니다. 이 창을 닫으면 서버도 종료됩니다.
pushd "%PROJECT_ROOT%"
call npm run dev
popd

echo 서버가 종료되었습니다.
pause
endlocal
