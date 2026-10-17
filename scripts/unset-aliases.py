#!/usr/bin/env python3
"""Remove git-enhanced aliases from the global git config.

    python unset-aliases.py

Lists the aliases installed by set-aliases.py (those pointing at a script in
~/.git-enhanced/), lets you tick the ones to remove, unsets them and deletes
their scripts. Aliases you created yourself are never touched.
Standard library only, Python 3.8+.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

INSTALL_DIR = (Path.home() / ".git-enhanced").resolve()
DESC_RE = re.compile(r"^#\s*Description:\s*(.+?)\s*$", re.IGNORECASE)


def ask(prompt):
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        sys.exit(1)


def alias_command(script_path):
    """Must match the value written by set-aliases.py."""
    quoted = "'" + script_path.as_posix().replace("'", "'\\''") + "'"
    return f"!bash {quoted}"


def read_description(path):
    try:
        with path.open(encoding="utf-8", errors="replace") as f:
            for _ in range(10):
                match = DESC_RE.match(f.readline().strip())
                if match:
                    return match.group(1)
    except OSError:
        pass
    return ""


def find_installed():
    """Global aliases whose value is exactly the one set-aliases.py writes."""
    result = subprocess.run(
        ["git", "config", "--global", "--get-regexp", r"^alias\."],
        capture_output=True, text=True,
    )
    if result.returncode != 0:  # no aliases at all
        return []
    installed = []
    for line in result.stdout.splitlines():
        key, _, value = line.partition(" ")
        name = key[len("alias."):]
        script = INSTALL_DIR / f"{name}.sh"
        if value.strip() == alias_command(script):
            installed.append({"name": name, "script": script,
                              "description": read_description(script)})
    return sorted(installed, key=lambda a: a["name"])


def select_aliases(aliases):
    ticked = set()
    width = max(len(a["name"]) for a in aliases)
    while True:
        print("\nInstalled aliases:\n")
        for i, alias in enumerate(aliases):
            box = "x" if i in ticked else " "
            print(f"  [{box}] {i + 1}. {alias['name']:<{width}}  {alias['description']}")
        answer = ask("\nType numbers to tick/untick the ones to REMOVE (e.g. 1 2),\n"
                     "'a' for all/none, or press Enter to confirm: ")
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


def remove(selected):
    print()
    for alias in selected:
        name = alias["name"]
        result = subprocess.run(
            ["git", "config", "--global", "--unset", f"alias.{name}"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"  Failed to unset '{name}': {result.stderr.strip()}")
            continue
        try:
            alias["script"].unlink(missing_ok=True)
        except OSError as exc:
            print(f"  Unset '{name}', but could not delete {alias['script']}: {exc}")
            continue
        print(f"  Removed '{name}'.")

    # Remove the install folder once nothing is left in it.
    try:
        INSTALL_DIR.rmdir()
        print(f"\nRemoved empty folder {INSTALL_DIR}.")
    except OSError:
        pass  # missing or still contains files


def main():
    if shutil.which("git") is None:
        print("git was not found on your PATH.")
        return 1

    installed = find_installed()
    if not installed:
        print("No git-enhanced aliases are installed.")
        return 0

    selected = select_aliases(installed)
    if not selected:
        print("\nNothing selected, nothing to do.")
        return 0

    remove(selected)
    return 0


if __name__ == "__main__":
    sys.exit(main())