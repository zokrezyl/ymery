#!/bin/bash
# Run the Step 1: Basic Widgets tutorial

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
uv run ymery --layouts-path "$SCRIPT_DIR" --main app
