#!/bin/bash

# Make it executable by : chmod +x setup.sh
# You can run it after cloning with: ./setup.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_message() {
    echo -e "${2}${1}${NC}"
}

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    print_message "Python 3 is not installed. Please install it first." "$RED"
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    print_message "pip3 is not installed. Please install it first." "$RED"
    exit 1
fi

# Check if git is installed
if ! command -v git &> /dev/null; then
    print_message "git is not installed. Please install it first." "$RED"
    exit 1
fi

# Check if ffmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    print_message "ffmpeg is not installed. Please install it first." "$RED"
    exit 1
fi

# Create virtual environment
print_message "Creating virtual environment..." "$YELLOW"
python3 -m venv .venv

# Activate virtual environment
print_message "Activating virtual environment..." "$YELLOW"
source .venv/bin/activate

# Install uv package manager
print_message "Installing uv package manager..." "$YELLOW"
pip3 install uv

# Install dependencies
print_message "Installing dependencies..." "$YELLOW"
uv pip install -e .

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    print_message "Creating .env file..." "$YELLOW"
    cp sample.env .env
    print_message "Please edit .env file with your credentials." "$GREEN"
fi

print_message "Setup completed successfully!" "$GREEN"
print_message "To start the bot, run: source .venv/bin/activate && tgmusic" "$GREEN"
