#!/usr/bin/env bash
# Render build script — installs Python deps + Playwright Chromium
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright Chromium with its system-level dependencies.
# --with-deps installs the required OS packages (libnss3, libatk, etc.)
# that headless Chromium needs on Render's Ubuntu-based environment.
playwright install --with-deps chromium
