#!/usr/bin/env bash
# rst: pull every repo, rebuild what changed, restart only the changed services.
#   rst      normal update
#   rst -f   restart everything even if nothing changed
set -euo pipefail

ROOT="${HH_ROOT:-$HOME}"
REPOS=(infra world)            # add runtime vm compiler houses monitoring when they appear
COMPOSE=(docker compose -f "$ROOT/infra/compose.yaml")

pull_repos() {
    echo "== pull"
    for repo in "${REPOS[@]}"; do
        local dir="$ROOT/$repo"
        if [[ ! -d "$dir/.git" ]]; then
            echo "   skip  $repo (no $dir)"
            continue
        fi
        local before after
        before=$(git -C "$dir" rev-parse --short HEAD)
        git -C "$dir" pull --ff-only --quiet
        after=$(git -C "$dir" rev-parse --short HEAD)
        if [[ "$before" == "$after" ]]; then
            echo "   same  $repo $after"
        else
            echo "   new   $repo $before -> $after"
        fi
    done
}

bring_up() {
    local extra=()
    [[ "${1:-}" == "-f" ]] && extra=(--force-recreate)
    echo "== up (containers with an unchanged image are left running)"
    "${COMPOSE[@]}" up -d --build --remove-orphans "${extra[@]}"
}

show_status() {
    echo "== status"
    "${COMPOSE[@]}" ps --format "table {{.Service}}\t{{.Status}}"
}

main() {
    pull_repos
    bring_up "${1:-}"
    show_status
}

main "$@"
