#!/usr/bin/env python3
"""
Version bumping script for ymery.

This script automatically bumps the version in pyproject.toml
and updates the CHANGELOG.md with a new version section.

Usage:
    python scripts/bump_version.py patch   # 0.0.1 -> 0.0.2
    python scripts/bump_version.py minor   # 0.0.1 -> 0.1.0
    python scripts/bump_version.py major   # 0.0.1 -> 1.0.0
"""

import sys
import re
from pathlib import Path
from datetime import datetime


def get_current_version():
    """Get current version from pyproject.toml"""
    pyproject_file = Path("pyproject.toml")
    content = pyproject_file.read_text()

    match = re.search(r'^version = ["\']([^"\']+)["\']', content, re.MULTILINE)
    if not match:
        raise ValueError("Could not find version in pyproject.toml")

    return match.group(1)


def parse_version(version_str):
    """Parse version string into major, minor, patch components"""
    parts = version_str.split('.')
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {version_str}")

    try:
        return [int(part) for part in parts]
    except ValueError:
        raise ValueError(f"Invalid version format: {version_str}")


def bump_version(current_version, bump_type):
    """Bump version according to bump_type"""
    major, minor, patch = parse_version(current_version)

    if bump_type == "patch":
        patch += 1
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    else:
        raise ValueError(f"Invalid bump type: {bump_type}")

    return f"{major}.{minor}.{patch}"


def update_pyproject_toml(new_version):
    """Update version in pyproject.toml"""
    pyproject_file = Path("pyproject.toml")
    content = pyproject_file.read_text()

    # Replace version (match at start of line)
    new_content = re.sub(
        r'^version = ["\'][^"\']+["\']',
        f'version = "{new_version}"',
        content,
        flags=re.MULTILINE
    )

    pyproject_file.write_text(new_content)
    print(f"✅ Updated pyproject.toml")


def update_pyodide_loader(new_version):
    """Update YMERY_VERSION in pyodide_loader.js"""
    loader_file = Path("docs/demo/js/pyodide_loader.js")

    if not loader_file.exists():
        print("⚠️  pyodide_loader.js not found, skipping")
        return

    content = loader_file.read_text()
    new_content = re.sub(
        r'const YMERY_VERSION = "[^"]+";',
        f'const YMERY_VERSION = "{new_version}";',
        content
    )
    loader_file.write_text(new_content)
    print(f"✅ Updated pyodide_loader.js")


def update_changelog(new_version):
    """Add new version section to CHANGELOG.md"""
    changelog_file = Path("CHANGELOG.md")

    if not changelog_file.exists():
        print("⚠️  CHANGELOG.md not found, skipping changelog update")
        return

    content = changelog_file.read_text()
    today = datetime.now().strftime("%Y-%m-%d")

    # Find the first ## heading (should be the latest version)
    lines = content.split('\n')
    insert_index = None

    for i, line in enumerate(lines):
        if line.startswith('## ['):
            insert_index = i
            break

    if insert_index is None:
        print("⚠️  Could not find version section in CHANGELOG.md, skipping changelog update")
        return

    # Create new version section
    new_section = [
        f"## [{new_version}] - {today}",
        "",
        "### Added",
        "- ",
        "",
        "### Changed",
        "- ",
        "",
        "### Fixed",
        "- ",
        "",
    ]

    # Insert new section
    lines[insert_index:insert_index] = new_section

    changelog_file.write_text('\n'.join(lines))
    print(f"✅ Updated CHANGELOG.md with version {new_version}")


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/bump_version.py <patch|minor|major>")
        sys.exit(1)

    bump_type = sys.argv[1].lower()
    if bump_type not in ["patch", "minor", "major"]:
        print("Error: bump type must be 'patch', 'minor', or 'major'")
        sys.exit(1)

    try:
        # Get current version
        current_version = get_current_version()
        print(f"📋 Current version: {current_version}")

        # Calculate new version
        new_version = bump_version(current_version, bump_type)
        print(f"🎯 New version: {new_version}")

        # Update files
        update_pyproject_toml(new_version)
        update_pyodide_loader(new_version)
        update_changelog(new_version)

        print(f"🎉 Successfully bumped {bump_type} version: {current_version} → {new_version}")
        print(f"📝 Don't forget to:")
        print(f"   1. Edit CHANGELOG.md to add actual changes")
        print(f"   2. Stage version files: git add pyproject.toml CHANGELOG.md docs/demo/js/pyodide_loader.js")
        print(f"   3. Commit: git commit -m 'Bump version to {new_version}'")
        print(f"   4. Upload: make upload (or make upload-test for TestPyPI)")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
