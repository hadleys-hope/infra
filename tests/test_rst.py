"""Exercise deployment decisions with fake git/docker; never contact a server."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

class RstTests(unittest.TestCase):
    def test_failed_build_retries_and_successful_unchanged_deploy_skips(self):
        script = Path(__file__).resolve().parents[1] / 'rst'
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for repo in ('world', 'infra'): (root / repo / '.git').mkdir(parents=True)
            binary = root / 'bin'; binary.mkdir()
            (binary / 'git').write_text('#!/bin/sh\ncase "$*" in *rev-parse*) echo abc123;; esac\n')
            (binary / 'docker').write_text('#!/bin/sh\necho "$*" >> "$HH_ROOT/calls"\ncase "$*" in *"up -d"*) test ! -f "$HH_ROOT/fail";; esac\n')
            for p in binary.iterdir(): p.chmod(0o755)
            env = dict(os.environ, HH_ROOT=str(root), XDG_STATE_HOME=str(root / 'state'),
                       XDG_RUNTIME_DIR=str(root), PATH=str(binary)+os.pathsep+os.environ['PATH'])
            run = lambda: subprocess.run(['bash', str(script), '--auto'], env=env, capture_output=True)
            (root / 'fail').touch()
            self.assertNotEqual(run().returncode, 0)
            self.assertFalse((root / 'state/hadleys-hope/deployed-heads').exists())
            (root / 'fail').unlink()
            self.assertEqual(run().returncode, 0)
            calls = (root / 'calls').read_text()
            self.assertEqual(calls.count('up -d'), 2)
            self.assertIn('--project-directory', calls)
            self.assertEqual(run().returncode, 0)
            self.assertEqual((root / 'calls').read_text(), calls)
if __name__ == '__main__': unittest.main()
