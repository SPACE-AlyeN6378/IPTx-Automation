#!/bin/bash

# Set your GitHub username and email
GIT_USERNAME="SPACE-AlyeN6378"
GIT_EMAIL="alymooltazeem@gmail.com"

# Set your GitHub repository URL
GITHUB_REPO_URL="https://github.com/SPACE-AlyeN6378/IPTx-Automation"

# Initialize Git repository
git init

# Configure Git user
git config --global user.name "$GIT_USERNAME"
git config --global user.email "$GIT_EMAIL"

git add .

# Commit changes
read -p "Enter your commit message: " COMMIT_MESSAGE
git commit -m "$COMMIT_MESSAGE"

git branch -M main

# Add GitHub repository as remote origin
git remote add origin "$GITHUB_REPO_URL"

# Push to GitHub (main branch)
git push -u origin main

echo "Configuration complete!"
