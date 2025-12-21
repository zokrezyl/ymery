#!/bin/bash
# Run the Step 7: Advanced Custom TreeLike tutorial

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Note: This demo requires the custom plugin to be loaded
uv run ymery --layouts-path "$SCRIPT_DIR" --plugins-path "$SCRIPT_DIR/plugins" --main app
