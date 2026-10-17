#!/usr/bin/env bash
# Description: Switch to the default branch, pull it, and delete the branch you came from

set -u

usage() {
    cat <<USAGE
Usage: git done [-r <remote>] [-f]

Check out the default branch, pull the latest changes, and delete the branch
you were on.

Options:
  -r <remote>  Remote to use (default: origin)
  -f           Force delete the branch (needed when it was squash-merged)
  -h           Show this help
USAGE
}

die() { echo "git done: $*" >&2; exit 1; }

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
force=0
while getopts ":r:fh" opt; do
    case $opt in
        r) remote=$OPTARG ;;
        f) force=1 ;;
        h) usage; exit 0 ;;
        :) usage >&2; die "option -$OPTARG requires an argument" ;;
        *) usage >&2; die "unknown option -$OPTARG" ;;
    esac
done

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "not inside a git repository"
git remote get-url "$remote" >/dev/null 2>&1 || die "remote '$remote' does not exist"

if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    die "you have uncommitted changes to tracked files; commit or stash them first"
fi

start=$(git symbolic-ref --quiet --short HEAD || true)   # empty when HEAD is detached
default=$(default_branch "$remote")
[ -n "$default" ] || die "could not determine the default branch of '$remote'"

# Checkout default branch
if [ "$start" != "$default" ]; then
    git checkout "$default" || die "could not check out '$default'"
fi

# Pull latest changes
git pull --ff-only "$remote" "$default" || die "could not fast-forward '$default' from '$remote'"

# Delete the branch we came from
if [ -z "$start" ]; then
    echo "HEAD was detached, nothing to delete."
elif [ "$start" = "$default" ]; then
    echo "Already on '$default', nothing to delete."
else
    tip=$(git rev-parse --short "$start")
    if [ "$force" -eq 1 ]; then
        git branch -D "$start" || die "could not delete '$start'"
        echo "Deleted '$start' (was $tip). Restore with: git branch $start $tip"
    elif ! git branch -d "$start"; then
        echo "git done: '$start' was not deleted (it is not fully merged)." >&2
        echo "If it was squash-merged, delete it with: git branch -D $start   (tip was $tip)" >&2
        exit 1
    fi
fi
