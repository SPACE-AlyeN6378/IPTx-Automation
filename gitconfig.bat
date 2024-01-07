@echo off

REM Set your GitHub username and email
set GIT_USERNAME=SPACE-AlyeN6378
set GIT_EMAIL=alymooltazeem@gmail.com

REM Set your GitHub repository URL
set GITHUB_REPO_URL=https://github.com/SPACE-AlyeN6378/IPTx-Automation

REM Initialize Git repository
git init

REM Configure Git user
git config --global user.name "%GIT_USERNAME%"
git config --global user.email "%GIT_EMAIL%"

git add .

REM Commit changes
set /p COMMIT_MESSAGE=Enter your commit message: 
git commit -m "%COMMIT_MESSAGE%"

git branch -M main

REM Add GitHub repository as remote origin
git remote add origin %GITHUB_REPO_URL%

REM Push to GitHub (master branch)
git push -u origin main

echo Configuration complete!
pause
