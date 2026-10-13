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

## Server hangs: logs and auto-reboot

`host/etc` and `host/usr` mirror files that live outside the repo on the server.
A root timer copies them in: every 5 minutes `host/hh-host-sync` installs the files that
differ from the live ones and restarts only what they affect (journald, `daemon-reexec`
for the watchdog, `daemon-reload` for units, docker). So a push to `host/` reaches the
system within ~6 minutes: `rst` pulls it, then the timer installs it.
A changed `daemon.json` restarts docker and with it every container.
Files deleted from `host/` are not deleted from the system.

One-time bootstrap (after this, edit `host/` in Git only, never `/etc` by hand):

```sh
ls /dev/watchdog*                      # the watchdog needs a hardware timer; `wdctl` shows it
cat /etc/docker/daemon.json            # keys not in host/etc/docker/daemon.json will be lost: move them there first
sudo cp ~/infra/host/etc/systemd/system/hh-host-sync@.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now hh-host-sync@$USER.timer
sudo systemctl start hh-host-sync@$USER.service    # first install right now
journalctl -u hh-host-sync@$USER                   # what was installed and restarted
rst -f                                 # Docker log rotation applies only to recreated containers
```

The timer runs, as root, a script from a checkout that pulls itself from GitHub: push access
to `infra` means root on the server. That was already true through `docker compose up --build`.

What it gives:

- the journal is persistent (`journald.conf.d/hh.conf`) and flushed every 30 s, so the
  last minutes before a hang survive the reboot;
- container logs rotate at 50 MB × 3 (`daemon.json`), so they cannot fill the disk;
- every container has `mem_limit` in `compose.yaml`: a leak gets that container
  OOM-killed and restarted instead of starving the whole machine;
- systemd pings the hardware watchdog (`RuntimeWatchdogSec=60`): a hung machine
  reboots itself after about a minute;
- `hh-health` (cron, every minute) logs load, memory, swap and disk usage.

After a hang, look at the previous boot:

```sh
journalctl --list-boots                            # did it reboot, and when
journalctl -b -1 -e                                # the end of the boot that hung
journalctl -b -1 -t hh-health | tail -30           # memory/swap/disk/load trend before the hang
journalctl -b -1 -k | grep -iE 'oom|killed process|hung_task|watchdog|i/o error'
docker inspect -f '{{.Name}} oom={{.State.OOMKilled}} restarts={{.RestartCount}}' $(docker ps -aq)
```

Growing `mem_used`/`swap_used` points to a leak (the OOM line names the process);
`disk/=100%` to logs or volumes; a flat trend that just stops points to hardware or kernel.

## Tests

Run the local deployment-logic test (mock git/docker, no server access):

```sh
python3 -m unittest discover -s tests -v   # rst and hh-host-sync
```
