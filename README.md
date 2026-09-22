# Hadley's Hope infrastructure

`infra/` and `world/` must be sibling Git checkouts. The existing `.env` needs
`ADMIN_TOKEN` and `DOMAIN`. Compose, services and persistent volumes are unchanged.

The world repository now contains a Python package, browser ES modules and
vendored Three.js assets. Its Dockerfile copies all of them. No Node/npm build
step is needed on the server. Keep the existing systemd service and timer.

`rst --auto` records the two successfully deployed Git revisions only after
`docker compose up --build` succeeds. Failed builds are retried by the next
run even if `git pull` has no further changes. State is kept outside Git in
`${XDG_STATE_HOME:-$HOME/.local/state}/hadleys-hope/deployed-heads`.
The first run after this change builds once to establish the marker.

Compose uses the explicit infra project directory, so `.env` resolution is
independent of the caller's current directory. A plain `rst` still runs the
build unconditionally; `rst -f` also recreates containers.

The timer pulls the branch directly; it does not wait for GitHub Actions.
The world CI validates modules, regression data, browser pages and the Docker
image. See `world/docs/DEPLOYMENT_RU.md` for migration and rollback details.

Run the local deployment-logic test (mock git/docker, no server access):

```sh
python3 -m unittest discover -s tests -v
```
