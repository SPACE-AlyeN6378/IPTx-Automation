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

REM Add GitHub repository as remote origin
git remote add origin %GITHUB_REPO_URL%

echo Configuration complete!
pause
