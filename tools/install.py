#!/usr/bin/env python3
"""Check for and install everything this project needs.

Each requirement is listed in REQUIREMENTS below, in the order it is checked.
To add one, append an entry with the command used to detect it and the
install command for each platform.

Usage:
  python3 tools/install.py           check each requirement, offer to install or upgrade
  python3 tools/install.py --check   only report what is installed, outdated or missing
  python3 tools/install.py --yes     install or upgrade without asking

Supported installers:
  macOS    Homebrew (brew)    https://brew.sh  (installed by this script if missing)
  Linux    apt (Debian/Ubuntu)
  Windows  winget

This script itself must run on Python 3.9 (the version built into macOS),
because it is what upgrades Python.
"""
from __future__ import annotations

import argparse
import glob
import os
import platform
import re
import shutil
import subprocess
import sys

HOMEBREW_INSTALL = (
    '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
)

# The Python version the project wants. Older versions are offered an upgrade.
MIN_PYTHON = (3, 13)

# name:         shown to the user
# command:      program that must be available
# module:       instead of command: a Python package that the project's Python
#               (the "Python" requirement below) must be able to import
# purpose:      why the project needs it
# platforms:    optional; only check on these platform.system() values
# paths:        optional; places to look before the PATH (checked in order)
# min_version:  optional; (major, minor) the installed version must reach
# install:      install command per platform.system() value
#               (a list is run directly; a string is run by the shell)
REQUIREMENTS = [
    {
        "name": "Homebrew",
        "command": "brew",
        "purpose": "installs the other requirements on macOS",
        "platforms": ["Darwin"],
        # Homebrew installs here and is not on the PATH until a new terminal is opened.
        "paths": ["/opt/homebrew/bin/brew", "/usr/local/bin/brew"],
        "install": {"Darwin": HOMEBREW_INSTALL},
    },
    {
        "name": "Python",
        "command": "python3",
        "purpose": "runs the scripts in tools/ and the API in api/",
        # Homebrew's Python first, so it wins over the older one built into macOS.
        "paths": ["/opt/homebrew/bin/python3", "/usr/local/bin/python3"],
        "min_version": MIN_PYTHON,
        "install": {
            # Installs the latest Python, or upgrades Homebrew's Python if it is outdated.
            "Darwin": ["brew", "install", "python"],
            "Linux": ["sudo", "apt-get", "install", "-y", "python3"],
            "Windows": ["winget", "install", "--id", "Python.Python.3.13", "-e"],
        },
    },
    {
        "name": "pandoc",
        "command": "pandoc",
        "purpose": "converts Markdown in data/md/ to HTML in bundle/",
        "install": {
            "Darwin": ["brew", "install", "pandoc"],
            "Linux": ["sudo", "apt-get", "install", "-y", "pandoc"],
            "Windows": ["winget", "install", "--id", "JohnMacFarlane.Pandoc", "-e"],
        },
    },
    {
        "name": "Node.js",
        "command": "node",
        "purpose": "runs mermaid-cli (the only non-Python step of the build)",
        "min_version": (20, 0),
        "install": {
            "Darwin": ["brew", "install", "node"],
            "Linux": ["sudo", "apt-get", "install", "-y", "nodejs", "npm"],
            "Windows": ["winget", "install", "--id", "OpenJS.NodeJS.LTS", "-e"],
        },
    },
    {
        "name": "mermaid-cli",
        "command": "mmdc",
        "purpose": "renders Mermaid diagrams in data/md/ to SVG in bundle/",
        # Version 12 or newer: its Mermaid includes the ELK layout (layout: elk),
        # which older versions needed the separate @mermaid-js/layout-elk package for.
        "min_version": (12, 0),
        # Installed with Node's npm, so Node.js must be installed first.
        # It downloads its own copy of Chrome (headless) the first time it is installed.
        "install": {
            "Darwin": ["npm", "install", "-g", "@mermaid-js/mermaid-cli"],
            "Linux": ["sudo", "npm", "install", "-g", "@mermaid-js/mermaid-cli"],
            "Windows": ["npm", "install", "-g", "@mermaid-js/mermaid-cli"],
        },
    },
    {
        "name": "Xcode",
        "command": "xcodebuild",
        "purpose": "builds and runs the iOS app in ios/",
        "platforms": ["Darwin"],
        # xcodebuild takes -version, not --version. Without the full Xcode app
        # (only the Command Line Tools), it prints an error instead of "Xcode <n>".
        "version_flag": "-version",
        "version_pattern": r"^Xcode \d",
        "install": {
            # Xcode comes only from the Mac App Store: this opens its page there.
            "Darwin": ["open", "macappstore://apps.apple.com/app/id497799835"],
        },
    },
]


REQUIREMENTS_BY_NAME = {r["name"]: r for r in REQUIREMENTS}


# Where Homebrew puts programs (Apple silicon, then Intel). Checked on macOS for
# every requirement, so tools installed by Homebrew are found even before
# Homebrew is on the PATH.
HOMEBREW_BIN_DIRS = ["/opt/homebrew/bin", "/usr/local/bin"]


def candidates(req: dict) -> list[str]:
    """Every place the requirement's command was found: known paths, the PATH,
    then Homebrew's folders on macOS."""
    places = list(req.get("paths", []))
    on_path = shutil.which(req["command"])
    if on_path:
        places.append(on_path)
    if platform.system() == "Darwin":
        places += [os.path.join(d, req["command"]) for d in HOMEBREW_BIN_DIRS]
    found = []
    for p in places:
        if p not in found and os.access(p, os.X_OK):
            found.append(p)
    return found


def version_of(path: str, flag: str = "--version") -> str:
    """Return the first line of `<path> --version` (or another flag), or an empty string."""
    try:
        result = subprocess.run([path, flag], capture_output=True, text=True, timeout=15)
        lines = (result.stdout or result.stderr).strip().splitlines()
        return lines[0] if lines else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def version_tuple(text: str) -> tuple[int, ...]:
    match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text)
    return tuple(int(n) for n in match.groups() if n is not None) if match else ()


def project_python() -> str | None:
    """The Python that meets MIN_PYTHON, or None."""
    python = next(r for r in REQUIREMENTS if r["name"] == "Python")
    state, path, _ = status(python)
    return path if state == "ok" else None


def module_status(req: dict) -> tuple[str, str | None, str]:
    """Whether the project's Python can import the requirement's module."""
    python = project_python()
    if python is None:
        return "missing", None, ""
    code = f"import {req['module']} as m; print(getattr(m, '__version__', ''))"
    try:
        result = subprocess.run([python, "-c", code], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return "missing", None, ""
    if result.returncode != 0:
        return "missing", None, ""
    return "ok", python, f"{req['module']} {result.stdout.strip()}".strip()


def status(req: dict) -> tuple[str, str | None, str]:
    """Return ("ok" | "outdated" | "missing", path, version line)."""
    if "module" in req:
        return module_status(req)
    best = None
    for path in candidates(req):
        line = version_of(path, req.get("version_flag", "--version"))
        if "version_pattern" in req and not re.search(req["version_pattern"], line):
            continue
        if "min_version" not in req or version_tuple(line) >= tuple(req["min_version"]):
            return "ok", path, line
        if best is None or version_tuple(line) > version_tuple(best[1]):
            best = (path, line)
    if best:
        return "outdated", best[0], best[1]
    return "missing", None, ""


def locate(command: str) -> str | None:
    """Find an installer command, including Homebrew before it is on the PATH."""
    for req in REQUIREMENTS:
        if req.get("command") == command:
            found = candidates(req)
            return found[0] if found else None
    return shutil.which(command)


def xcode_not_selected() -> bool:
    """If the Xcode app is installed but xcode-select points elsewhere (usually the
    Command Line Tools), say how to switch to it and return True."""
    apps = sorted(glob.glob("/Applications/Xcode*.app"))
    if not apps:
        return False
    try:
        selected = subprocess.run(["xcode-select", "-p"], capture_output=True, text=True, timeout=15).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        selected = "unknown"
    app = apps[0]
    print(f"  {app} is installed, but the developer tools in use are {selected or 'not set'}.")
    print("  Switch to Xcode and accept its license, then run this again:")
    print(f"    sudo xcode-select -s {app}/Contents/Developer")
    print("    sudo xcodebuild -license accept")
    return True


def ask(question: str) -> bool:
    try:
        return input(f"{question} [y/N] ").strip().lower() in ("y", "yes")
    except EOFError:
        return False


def install(req: dict, system: str, assume_yes: bool, verb: str) -> bool:
    cmd = req["install"].get(system)
    if cmd is None:
        print(f"  No install command for {system}. {verb.capitalize()} {req['name']} manually.")
        return False

    if req["name"] == "mermaid-cli" and status(REQUIREMENTS_BY_NAME["Node.js"])[0] != "ok":
        print("  Install Node.js first, then run this again.")
        return False

    if isinstance(cmd, list) and "module" in req:
        python = project_python()
        if python is None:
            print("  Install Python first, then run this again.")
            return False
        cmd = [python if part == "python3" else part for part in cmd]

    if isinstance(cmd, list):
        installer = locate(cmd[0]) if os.sep not in cmd[0] else cmd[0]
        if installer is None:
            print(f"  The installer '{cmd[0]}' was not found. Install it first, then run this again.")
            return False
        cmd = [installer, *cmd[1:]]
        shown = " ".join(cmd)
    else:
        shown = cmd

    print(f"  Command: {shown}")
    if not assume_yes and not ask(f"  {verb.capitalize()} {req['name']} now?"):
        print("  Skipped.")
        return False

    if subprocess.run(cmd, shell=isinstance(cmd, str)).returncode != 0:
        print(f"  Could not {verb} {req['name']}.")
        return False

    if req["name"] == "Xcode":
        print("  Install Xcode from the App Store page that opened, open it once to finish setup, then run this again.")
        return False

    state, path, line = status(req)
    if state == "missing":
        print(f"  {req['name']} was installed but could not be found. Open a new terminal and run this again.")
        return False
    if state == "outdated":
        print(f"  {req['name']} is still {line}, older than {'.'.join(map(str, req['min_version']))}.")
        return False
    print(f"  Done: {line or req['name']} at {path}")
    if "command" in req and shutil.which(req["command"]) != path:
        print(f"  Note: '{req['command']}' in your terminal does not run this one yet. "
              "Follow the installer's 'Next steps', or open a new terminal.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Check for and install project requirements.")
    parser.add_argument("--check", action="store_true", help="only report status; install nothing")
    parser.add_argument("--yes", action="store_true", help="install or upgrade without asking")
    args = parser.parse_args()

    system = platform.system()
    print(f"Platform: {system}. Running on Python {platform.python_version()}.\n")

    problems = []
    for req in REQUIREMENTS:
        if "platforms" in req and system not in req["platforms"]:
            continue
        print(f"{req['name']}: {req['purpose']}")
        state, path, line = status(req)
        if state == "ok":
            print(f"  OK: {line or 'installed'}")
            continue
        if state == "outdated":
            wanted = ".".join(map(str, req["min_version"]))
            print(f"  Outdated: {line} at {path}. Version {wanted} or newer is wanted.")
            verb = "upgrade"
        else:
            print("  Missing.")
            verb = "install"
        if req["name"] == "Xcode" and xcode_not_selected():
            problems.append("Xcode (not selected)")
            continue
        if args.check or not install(req, system, args.yes, verb):
            problems.append(f"{req['name']} ({state})")

    print()
    if problems:
        print(f"Still needed: {', '.join(problems)}")
        return 1
    print("Everything is installed and up to date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
