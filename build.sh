#!/bin/bash

# Update package manager
apt-get update

# Install Chrome
apt-get install -y chromium-browser

# Install ChromeDriver
apt-get install -y chromium-chromedriver

# Run pip install
pip install -r requirements.txt
