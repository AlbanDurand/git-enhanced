# Git Enhanced

A collection of git aliases, each one a standalone bash script in `aliases/`.

## Aliases

### `git done [-r <remote>] [-f]`

Finish with the current branch: check out the default branch, pull the latest
changes, and delete the branch you came from.

- `-r <remote>`: remote to use (default: `origin`)
- `-f`: force delete the branch. Needed when it was squash-merged, because git
  can't tell it has been merged. The deleted tip's SHA is printed so you can
  restore it with `git branch <name> <sha>`.
- If you start on the default branch, nothing is deleted.
- The pull is fast-forward only. Uncommitted changes to tracked files abort
  the command before anything happens.

### `git rebase-default [-r <remote>]`

Without leaving your branch: update the local default branch from the remote,
then rebase your branch onto it.

- `-r <remote>`: remote to use (default: `origin`)
- If you are on the default branch, it only pulls (fast-forward only).
- On conflicts it stops. Use `git rebase --continue` or `git rebase --abort`.

The default branch is detected from the remote (`git ls-remote --symref`),
falling back to the local `origin/HEAD`, then to `main` / `master`.

## Installation

Requirements: git, bash, Python 3.8+. On Windows, use
[Git for Windows](https://gitforwindows.org/), which provides bash.

```
git clone <repository-url>
cd git-enhanced
python scripts/set-aliases.py
```

The script lists the available aliases. Type a number to tick or untick it
(`a` toggles all), then press Enter. If an alias with the same name already
exists in your global git config, you choose whether to replace or skip it.

Selected scripts are copied to `~/.git-enhanced/` and the aliases are added to
your global git config pointing at those copies. At the end, the script offers
to delete the local clone; the aliases keep working either way.

## Updating

Clone the repository again and re-run `set-aliases.py`. Aliases that are
already installed are refreshed in place.

## Uninstalling

Run `python scripts/unset-aliases.py` from a clone of the repository. It lists the
installed git-enhanced aliases, you tick the ones to remove, and it unsets them
and deletes their scripts from `~/.git-enhanced/` (the folder itself goes once
it is empty). Aliases you created yourself are never touched.

To do it by hand instead:

```
git config --global --unset alias.done
git config --global --unset alias.rebase-default
```

Then delete `~/.git-enhanced/`.

## Adding a new alias

Drop `<alias-name>.sh` into `aliases/` with a `# Description: ...` comment near
the top. The installer picks it up automatically.