#!/bin/bash
# Run the Step 2: Data Binding tutorial

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
uv run ymery --layouts-path "$SCRIPT_DIR" --main app
