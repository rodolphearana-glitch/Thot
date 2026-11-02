@echo off
rem Lance le labo Thot sous Windows.
rem Il se met a jour tout seul depuis GitHub (voir thot\synchro.py) : plus besoin de retelecharger le ZIP.
cd /d "%~dp0"
setlocal

where git >nul 2>nul
if errorlevel 1 (
  echo Git n'est pas installe : Thot marchera, mais sans mise a jour automatique.
  echo Pour l'activer : https://git-scm.com/download/win
  goto installer
)

rem Une copie venue d'un ZIP n'est pas reliee a GitHub : on la relie une fois.
rem Seuls les fichiers du depot sont remis a jour ; .venv, thot.config.toml et tes sessions restent.
if not exist .git (
  echo Liaison de ce dossier avec GitHub...
  git init -q
  git remote add origin https://github.com/rodolphearana-glitch/Thot.git
  git fetch origin main
  if errorlevel 1 goto installer
  git reset -q --hard origin/main
  git branch -q -M main
  git branch -q -u origin/main
)
git config user.name >nul 2>nul || git config user.name "Thot (PC de Rodolphe)"
git config user.email >nul 2>nul || git config user.email "thot@localhost"

:installer
if not exist .venv (
  echo Premiere installation...
  py -3 -m venv .venv || python -m venv .venv
  .venv\Scripts\python -m pip install --upgrade pip
)
if not exist thot.config.toml (
  copy thot.config.example.toml thot.config.toml >nul
  echo Un fichier thot.config.toml a ete cree : Claude Code et Codex de ce PC, sans cle.
)

set OPTIONS=
:lancer
.venv\Scripts\python -m pip install -q -r requirements.txt
.venv\Scripts\python -m thot %OPTIONS% %*
if errorlevel 3 if not errorlevel 4 (
  echo Nouvelle version installee, Thot redemarre...
  set OPTIONS=--sans-navigateur
  goto lancer
)
pause
