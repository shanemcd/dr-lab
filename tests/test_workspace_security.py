"""Workspace handback must treat configured paths as data, not shell code."""
from pathlib import Path
import os
import shlex
import subprocess
import tempfile
import unittest

from jinja2 import Environment, StrictUndefined
import yaml

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / 'ansible_collections/shanemcd/dr_lab/roles/workspace/tasks/handback.yml'


class WorkspaceSecurityTests(unittest.TestCase):
    def test_generated_credential_names_are_gitignored(self):
        paths = ['local.yml', 'pull-secret.txt', 'secrets/lab_ed25519',
                 'dr-primary.kubeconfig', 'install-config.yaml.pristine',
                 'auth/kubeadmin-password', 'bootstrap.ign']
        result = subprocess.run(['git', 'check-ignore', '--stdin'], cwd=ROOT,
                                input='\n'.join(paths) + '\n', text=True,
                                capture_output=True, check=True)
        self.assertEqual(set(result.stdout.splitlines()), set(paths))

    def test_handback_quotes_paths_and_does_not_dereference_symlinks(self):
        task = yaml.safe_load(TASKS.read_text())[0]
        env = Environment(undefined=StrictUndefined)
        env.filters['quote'] = shlex.quote
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            workspace = base / 'workspace; touch INJECTED; # with spaces'
            workspace.mkdir()
            artifact = workspace / 'artifact with spaces'
            artifact.touch()
            outside = base / 'outside'
            outside.touch()
            (workspace / 'external-link').symlink_to(outside)
            # Use a fake chown to inspect the actual argv; never change ownership
            # or require privilege on the test runner.
            binary = base / 'bin'
            binary.mkdir()
            recorder = binary / 'chown'
            recorder.write_text('#!/usr/bin/env python3\n'
                                'import json, os, sys\n'
                                'open(os.environ["ARGV_RECORD"], "w").write(json.dumps(sys.argv[1:]))\n')
            recorder.chmod(0o755)
            record = base / 'argv.json'
            script = env.from_string(task['ansible.builtin.shell']).render(
                item=str(workspace), lab_workspace_identity=dict(uid=1234, gid=5678))
            # The production task selects root-owned artifacts. Adapt only that
            # predicate for non-root runners while testing the exact shell body.
            script = script.replace('-user root', f'-uid {os.getuid()}')
            subprocess.run(['bash', '-c', script], cwd=base, check=True,
                           env={**os.environ, 'PATH': f'{binary}:{os.environ["PATH"]}',
                                'ARGV_RECORD': str(record)})
            import json
            args = json.loads(record.read_text())
            self.assertEqual(args[:3], ['-h', '--', '1234:5678'])
            self.assertIn(str(artifact), args)
            self.assertIn(str(workspace / 'external-link'), args)
            self.assertNotIn(str(outside), args)
            self.assertFalse((base / 'INJECTED').exists())


if __name__ == '__main__':
    unittest.main()
