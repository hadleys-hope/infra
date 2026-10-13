"""Run host/hh-host-sync into a temp dir with fake systemctl/dockerd."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

class HostSyncTests(unittest.TestCase):
    def test_installs_changed_files_and_restarts_only_affected(self):
        script = Path(__file__).resolve().parents[1] / 'host' / 'hh-host-sync'
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            dest = root / 'dest'
            binary = root / 'bin'; binary.mkdir()
            for name in ('systemctl', 'dockerd'):
                (binary / name).write_text(f'#!/bin/sh\necho "{name} $*" >> "{root}/calls"\n')
                (binary / name).chmod(0o755)
            env = dict(os.environ, HH_DEST=str(dest), PATH=str(binary)+os.pathsep+os.environ['PATH'])
            run = lambda: subprocess.run(['sh', str(script)], env=env, check=True, capture_output=True)
            calls = lambda: (root / 'calls').read_text() if (root / 'calls').exists() else ''
            run()
            self.assertTrue((dest / 'etc/cron.d/hh-health').is_file())
            self.assertTrue(os.access(dest / 'usr/local/bin/hh-health', os.X_OK))
            for c in ('daemon-reexec', 'restart systemd-journald', 'restart docker', 'dockerd --validate'):
                self.assertIn(c, calls())
            (root / 'calls').unlink()
            run()
            self.assertEqual(calls(), '')
            (dest / 'etc/cron.d/hh-health').write_text('old\n')
            run()
            self.assertEqual(calls(), '')
            self.assertEqual((dest / 'etc/cron.d/hh-health').read_text(),
                             (script.parent / 'etc/cron.d/hh-health').read_text())
if __name__ == '__main__': unittest.main()
