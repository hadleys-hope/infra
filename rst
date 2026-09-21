#!/usr/bin/env bash
# rst: pull every repo, rebuild what changed, restart only the changed services.
#   rst         pull and bring everything up (unchanged containers keep running)
#   rst -f      restart everything even if nothing changed
#   rst --auto  for the timer: silent and does nothing unless some repo moved
set -euo pipefail

ROOT="${HH_ROOT:-$HOME}"
REPOS=(infra world)            # add runtime vm compiler houses monitoring when they appear
COMPOSE=(docker compose -f "$ROOT/infra/compose.yaml")
LOCK="${XDG_RUNTIME_DIR:-/tmp}/rst.lock"
MODE="${1:-}"
CHANGED=0
export GIT_TERMINAL_PROMPT=0   # never hang on a password prompt

say() {
    [[ "$MODE" == "--auto" && "${2:-}" != "always" ]] && return 0
    echo "$1"
}

take_lock() {
    exec 9>"$LOCK"
    if ! flock -n 9; then
        echo "== another rst is running, skip"
        exit 0
    fi
}

pull_repos() {
    say "== pull"
    for repo in "${REPOS[@]}"; do
        local dir="$ROOT/$repo"
        if [[ ! -d "$dir/.git" ]]; then
            say "   skip  $repo (no $dir)" always
            continue
        fi
        local before after
        before=$(git -C "$dir" rev-parse --short HEAD)
        git -C "$dir" pull --ff-only --quiet
        after=$(git -C "$dir" rev-parse --short HEAD)
        if [[ "$before" == "$after" ]]; then
            say "   same  $repo $after"
        else
            CHANGED=1
            say "   new   $repo $before -> $after" always
        fi
    done
}

bring_up() {
    local extra=()
    [[ "$MODE" == "-f" ]] && extra=(--force-recreate)
    say "== up (containers with an unchanged image are left running)" always
    "${COMPOSE[@]}" up -d --build --remove-orphans "${extra[@]}"
}

show_status() {
    say "== status" always
    "${COMPOSE[@]}" ps --format "table {{.Service}}\t{{.Status}}"
}

main() {
    take_lock
    pull_repos
    if [[ "$MODE" == "--auto" && "$CHANGED" -eq 0 ]]; then
        exit 0
    fi
    bring_up
    show_status
}

main
