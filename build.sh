#!/usr/bin/env bash
# Render build script — installs Python deps + Playwright Chromium
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# Store Playwright browsers inside the project directory so they survive
# from build into runtime (Render wipes ~/.cache between build and deploy).
export PLAYWRIGHT_BROWSERS_PATH=/opt/render/project/.playwright

# Install Playwright Chromium with its system-level dependencies.
playwright install --with-deps chromium

echo "Chromium installed at: $PLAYWRIGHT_BROWSERS_PATH"
ls -la "$PLAYWRIGHT_BROWSERS_PATH" || true
