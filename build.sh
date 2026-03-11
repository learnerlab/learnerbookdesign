#!/usr/bin/env bash
# Render build script — installs Python deps + Playwright Chromium
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# Store Playwright browsers inside the project directory so they survive
# from build into runtime (Render wipes ~/.cache between build and deploy).
export PLAYWRIGHT_BROWSERS_PATH=/opt/render/project/.playwright

# Install Playwright Chromium (without --with-deps to avoid su/sudo failures
# on Render). Render's base image includes most required system libraries.
playwright install chromium

echo "Chromium installed at: $PLAYWRIGHT_BROWSERS_PATH"
ls -la "$PLAYWRIGHT_BROWSERS_PATH" || true
