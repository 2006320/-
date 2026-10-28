@echo off
cd /d "%~dp0"
if not exist .env (
  copy .env.example .env
  echo Edit .env to set TWO secure passwords, then rerun this file.
  pause
  exit /b 1
)
docker compose up -d --build
start http://localhost:8501
pause
