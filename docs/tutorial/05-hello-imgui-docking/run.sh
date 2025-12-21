#!/bin/bash
# Run the Step 5: Hello ImGui Docking tutorial

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
uv run ymery --layouts-path "$SCRIPT_DIR" --main app
