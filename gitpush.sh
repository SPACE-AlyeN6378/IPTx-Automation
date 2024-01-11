#!/bin/bash

# Initialize Git repository
git init

# Set remote origin
git remote -v

# Add all files to staging
git add .

# Commit changes
read -p "Enter your commit message: " COMMIT_MESSAGE
git commit -m "$COMMIT_MESSAGE"

# Push to GitHub (main branch)
git push -u origin main

echo "Upload to GitHub complete!"
