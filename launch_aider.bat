@echo off
title Launching Aider - Scriptorium

:: Set your Deepseek API key
set DEEPSEEK_API_KEY=your_api_key_here

:: Navigate to the project directory
cd /d C:\Scriptorium

:: Launch Aider (it will automatically read .aider.conf.yml)
echo Starting Aider...
aider

pause