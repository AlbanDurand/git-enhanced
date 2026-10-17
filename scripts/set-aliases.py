#!/usr/bin/env python3
"""Install git-enhanced aliases into the global git config.

Run from a clone of the repository:

    python set-aliases.py

The selected scripts are copied to ~/.git-enhanced/, and the git aliases point
to those copies. The clone can therefore be deleted after installation.
Standard library only, Python 3.8+.
"""

import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent
ALIASES_DIR = REPO_DIR / "../aliases"
INSTALL_DIR = (Path.home() / ".git-enhanced").resolve()

NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9-]*$")
DESC_RE = re.compile(r"^#\s*Description:\s*(.+?)\s*$", re.IGNORECASE)


# --------------------------------------------------------------------------
# Prompts
# --------------------------------------------------------------------------

def ask(prompt):
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        sys.exit(1)


def ask_replace_or_skip():
    while True:
        answer = ask("Replace it or skip? [r/s]: ").lower()
        if answer in ("r", "replace"):
            return True
        if answer in ("s", "skip"):
            return False


def ask_yes_no(prompt):
    """Yes/no question, defaulting to no."""
    while True:
        answer = ask(f"{prompt} [y/N]: ").lower()
        if answer in ("", "n", "no"):
            return False
        if answer in ("y", "yes"):
            return True


# --------------------------------------------------------------------------
# Alias discovery and selection
# --------------------------------------------------------------------------

def read_description(path):
    with path.open(encoding="utf-8", errors="replace") as f:
        for _ in range(10):
            match = DESC_RE.match(f.readline().strip())
            if match:
                return match.group(1)
    return ""


def discover_aliases():
    if not ALIASES_DIR.is_dir():
        return []
    return [
        {"name": p.stem, "path": p, "description": read_description(p)}
        for p in sorted(ALIASES_DIR.glob("*.sh"))
        if NAME_RE.match(p.stem)
    ]


def select_aliases(aliases):
    ticked = set()
    width = max(len(a["name"]) for a in aliases)
    while True:
        print("\nAvailable aliases:\n")
        for i, alias in enumerate(aliases):
            box = "x" if i in ticked else " "
            print(f"  [{box}] {i + 1}. {alias['name']:<{width}}  {alias['description']}")
        answer = ask("\nType numbers to tick/untick (e.g. 1 2), 'a' for all/none,\n"
                     "or press Enter to confirm: ")
        if not answer:
            return [aliases[i] for i in sorted(ticked)]
        for token in re.split(r"[,\s]+", answer.lower()):
            if not token:
                continue
            if token == "a":
                ticked = set() if len(ticked) == len(aliases) else set(range(len(aliases)))
            elif token.isdigit() and 1 <= int(token) <= len(aliases):
                ticked ^= {int(token) - 1}
            else:
                print(f"Ignored: {token!r}")


# --------------------------------------------------------------------------
# Installation
# --------------------------------------------------------------------------

def git_config_get(name):
    result = subprocess.run(
        ["git", "config", "--global", "--get", f"alias.{name}"],
        capture_output=True, text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def git_config_set(name, value):
    result = subprocess.run(
        ["git", "config", "--global", f"alias.{name}", value],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  Failed to set alias '{name}': {result.stderr.strip()}")
        return False
    return True


def alias_command(script_path):
    """Alias value: run the script with bash. Forward slashes work on Windows too."""
    quoted = "'" + script_path.as_posix().replace("'", "'\\''") + "'"
    return f"!bash {quoted}"


def copy_script(source, target):
    # Normalise line endings so bash never sees CRLF.
    data = source.read_bytes().replace(b"\r\n", b"\n")
    target.write_bytes(data)
    target.chmod(target.stat().st_mode | stat.S_IXUSR)


def install(selected):
    """Install the selected aliases. Returns the names that are now in place."""
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    in_place = []
    print()
    for alias in selected:
        name = alias["name"]
        target = INSTALL_DIR / f"{name}.sh"
        command = alias_command(target)
        existing = git_config_get(name)

        if existing is not None and existing != command:
            print(f"An alias named '{name}' already exists:\n  alias.{name} = {existing}")
            if not ask_replace_or_skip():
                print(f"  Skipped '{name}'.\n")
                continue

        copy_script(alias["path"], target)
        if existing == command:
            print(f"  '{name}' was already installed (script refreshed).")
            in_place.append(name)
        elif git_config_set(name, command):
            print(f"  Installed '{name}'.")
            in_place.append(name)
    return in_place


# --------------------------------------------------------------------------
# Optional cleanup of the local repository copy
# --------------------------------------------------------------------------

def is_inside(child, parent):
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _make_writable_and_retry(func, path, _exc):
    # .git contains read-only files on Windows.
    os.chmod(path, stat.S_IWRITE)
    func(path)


def offer_repo_deletion():
    home = Path.home().resolve()
    unsafe = (
        REPO_DIR in (home, REPO_DIR.parent)
        or is_inside(INSTALL_DIR, REPO_DIR)
        or is_inside(REPO_DIR, INSTALL_DIR)
        or not (REPO_DIR / "set-aliases.py").is_file()
    )
    if unsafe:
        print(f"\nNot offering to delete {REPO_DIR} (unexpected location).")
        return

    print("\nThe installed aliases run from their own copy in:")
    print(f"  {INSTALL_DIR}")
    print("so the local copy of the repository is no longer needed.")
    if not ask_yes_no(f"Delete the local copy of the repository ({REPO_DIR})?"):
        print("Kept.")
        return

    os.chdir(REPO_DIR.parent)  # Don't sit inside the folder being removed.
    try:
        if sys.version_info >= (3, 12):
            shutil.rmtree(REPO_DIR, onexc=_make_writable_and_retry)
        else:
            shutil.rmtree(REPO_DIR, onerror=_make_writable_and_retry)
        print("Deleted.")
    except OSError as exc:
        print(f"Could not delete it completely: {exc}")
        print("Close any terminal or editor using that folder and delete it manually.")


# --------------------------------------------------------------------------

def main():
    if shutil.which("git") is None:
        print("git was not found on your PATH.")
        return 1
    if REPO_DIR.resolve() == INSTALL_DIR:
        print(f"This repository is cloned into {INSTALL_DIR}, which is where the")
        print("aliases get installed. Clone it somewhere else and run this again.")
        return 1

    aliases = discover_aliases()
    if not aliases:
        print(f"No aliases found in {ALIASES_DIR}.")
        return 1

    selected = select_aliases(aliases)
    if not selected:
        print("\nNothing selected, nothing to do.")
        return 0

    in_place = install(selected)
    if not in_place:
        print("\nNo aliases were installed.")
        return 0

    print("\nDone. Try: " + ", ".join(f"git {n}" for n in in_place))
    offer_repo_deletion()
    return 0


if __name__ == "__main__":
    sys.exit(main())
