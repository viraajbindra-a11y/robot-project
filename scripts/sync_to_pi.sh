#!/bin/bash

# Sync the project files to the Raspberry Pi
# Define the Raspberry Pi's IP address and the target directory
PI_IP="192.168.1.100"
TARGET_DIR="/home/pi/robot-project"

# Add the GitHub repository URL
GITHUB_REPO="git@github.com:yourusername/robot-project.git"

# Push changes to GitHub
git add .
git commit -m "Syncing project files to Raspberry Pi"
git push $GITHUB_REPO

# SSH into the Raspberry Pi and pull the latest changes
ssh pi@$PI_IP "cd $TARGET_DIR && git pull $GITHUB_REPO"