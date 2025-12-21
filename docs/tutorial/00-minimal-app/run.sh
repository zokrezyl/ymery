#!/bin/bash
# Run the Step 0: Minimal App tutorial

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Run ymery with this directory as the layouts path
uv run ymery --layouts-path "$SCRIPT_DIR" --main app
