@echo off
set "PATH=%PATH%;%LOCALAPPDATA%\Programs\GitHub CLI"
gh workflow run f1-research.yml --repo madpole360/operacion-pit-lane
echo %date% %time% - Workflow triggered >> %~dp0trigger-log.txt
