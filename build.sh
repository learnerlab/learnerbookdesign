#!/usr/bin/env bash
# Render build script — installs Python deps
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

echo "Build complete — no browser dependencies needed."
