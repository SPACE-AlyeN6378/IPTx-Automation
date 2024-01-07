@echo off

REM Initialize Git repository
git init

REM Set remote origin
git remote -v

REM Add all files to staging
git add .

REM Commit changes
set /p COMMIT_MESSAGE=Enter your commit message: 
git commit -m "%COMMIT_MESSAGE%"

REM Push to GitHub (master branch)
git push -u origin main

echo Upload to GitHub complete!
pause
