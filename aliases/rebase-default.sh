#!/usr/bin/env bash
# Description: Update the default branch from the remote and rebase the current branch onto it

set -u

usage() {
    cat <<USAGE
Usage: git rebase-default [-r <remote>]

Update the local default branch from the remote (without leaving the current
branch), then rebase the current branch onto it. On the default branch itself,
only the pull is done.

Options:
  -r <remote>  Remote to use (default: origin)
  -h           Show this help
USAGE
}

die() { echo "git rebase-default: $*" >&2; exit 1; }

# Print the default branch name of remote $1 (empty if it can't be determined).
default_branch() {
    local remote=$1 ref c
    ref=$(git ls-remote --symref "$remote" HEAD 2>/dev/null \
        | awk '/^ref:/ { sub("refs/heads/", "", $2); print $2; exit }')
    if [ -z "$ref" ]; then
        ref=$(git symbolic-ref --quiet --short "refs/remotes/$remote/HEAD" 2>/dev/null)
        ref=${ref#"$remote"/}
    fi
    if [ -z "$ref" ]; then
        for c in main master; do
            if git show-ref --verify --quiet "refs/heads/$c" \
                || git show-ref --verify --quiet "refs/remotes/$remote/$c"; then
                ref=$c
                break
            fi
        done
    fi
    printf '%s' "$ref"
}

remote=origin
while getopts ":r:h" opt; do
    case $opt in
        r) remote=$OPTARG ;;
        h) usage; exit 0 ;;
        :) usage >&2; die "option -$OPTARG requires an argument" ;;
        *) usage >&2; die "unknown option -$OPTARG" ;;
    esac
done

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "not inside a git repository"
git remote get-url "$remote" >/dev/null 2>&1 || die "remote '$remote' does not exist"

current=$(git symbolic-ref --quiet --short HEAD || true)
[ -n "$current" ] || die "HEAD is detached; check out a branch first"

if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    die "you have uncommitted changes to tracked files; commit or stash them first"
fi

default=$(default_branch "$remote")
[ -n "$default" ] || die "could not determine the default branch of '$remote'"

if [ "$current" = "$default" ]; then
    # The default branch is checked out, so it can't be updated by a fetch.
    git pull --ff-only "$remote" "$default" || die "could not fast-forward '$default' from '$remote'"
    echo "On '$default': pulled, nothing to rebase."
    exit 0
fi

# Update local default branch without checking it out (fast-forward only).
git fetch "$remote" "refs/heads/$default:refs/heads/$default" \
    || die "could not fast-forward local '$default' from '$remote'"

if ! git rebase "$default"; then
    echo "git rebase-default: rebase stopped. Resolve the conflicts, then run" >&2
    echo "'git rebase --continue' (or 'git rebase --abort' to cancel)." >&2
    exit 1
fi
