@echo off
rem Scriptorium - stage the complete working tree, commit and push safely.
rem
rem Replaces the old version, which only staged three hard-coded files and
rem kept going after a failed commit/push while still printing "complete" -
rem see notes\01_Active\notes_011.txt Finding 1.

cd /d "C:\Scriptorium" || exit /b 1
setlocal

set "COMMIT_MSG=%~1"
if not defined COMMIT_MSG set /p "COMMIT_MSG=Enter commit message: "
if not defined COMMIT_MSG (
    echo No commit message provided. Aborting update.
    pause
    exit /b 1
)

echo Staging the full working tree...
git add --all || goto :failed

git diff --cached --quiet
if not errorlevel 1 (
    echo No staged changes to commit.
    exit /b 0
)

echo Committing changes...
git commit -m "%COMMIT_MSG%" || goto :failed

echo Pushing to GitHub...
git push origin main || goto :failed

echo.
git status --short
echo Repository update complete.
pause
exit /b 0

:failed
echo.
echo Repository update FAILED - review the Git error above. Nothing further
echo was attempted.
pause
exit /b 1
