@echo off
rem Lance le labo Thot sous Windows.
cd /d "%~dp0"
if not exist .venv (
  echo Premiere installation...
  py -3 -m venv .venv || python -m venv .venv
  .venv\Scripts\python -m pip install --upgrade pip
  .venv\Scripts\python -m pip install -r requirements.txt
)
if not exist thot.config.toml (
  copy thot.config.example.toml thot.config.toml >nul
  echo Un fichier thot.config.toml a ete cree : Claude Code et Codex de ce PC, sans cle.
)
.venv\Scripts\python -m thot
pause
