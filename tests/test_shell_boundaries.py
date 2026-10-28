"""Execute rendered shell boundaries without credentials or live infrastructure."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

from jinja2 import Environment, StrictUndefined
import yaml

ROOT = Path(__file__).resolve().parents[1]
ROLES = ROOT / "ansible_collections/shanemcd/dr_lab/roles"


class ShellBoundaryTests(unittest.TestCase):
    def test_acm_import_preserves_literal_paths_and_pipe_failure(self):
        tasks = yaml.safe_load((ROLES / "acm/tasks/spoke.yml").read_text())
        task = next(t for t in tasks if t["name"] == "Ensure the spoke auto-import secret")
        self.assertTrue(task["no_log"])
        env = Environment(undefined=StrictUndefined)
        env.filters["quote"] = shlex.quote
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            bindir = base / "bin ' $(touch INJECTED)"
            bindir.mkdir()
            fake = bindir / "oc"
            fake.write_text("#!/usr/bin/env python3\n"
                            "import json, os, sys\n"
                            "with open(os.environ['CALLS'], 'a') as f:\n"
                            "    f.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                            "if sys.argv[1] == 'create':\n"
                            "    print('fixture-not-a-secret')\n"
                            "    sys.exit(int(os.environ.get('CREATE_RC', '0')))\n"
                            "assert sys.stdin.read() == 'fixture-not-a-secret\\n'\n")
            fake.chmod(0o755)
            install = str(base / "workspace ' $(touch INJECTED)")
            script = env.from_string(task["ansible.builtin.shell"]).render(
                install_bin_dir=str(bindir), install_base_dir=install,
                acm_spoke_name="dr-primary")
            calls = base / "calls.jsonl"
            process_env = dict(os.environ, CALLS=str(calls))
            result = subprocess.run(["bash", "-c", script], cwd=tmp,
                                    env=process_env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            args = [json.loads(line) for line in calls.read_text().splitlines()]
            create = next(a for a in args if a[0] == "create")
            self.assertIn("--from-file=kubeconfig=" + install + "/dr-primary/auth/kubeconfig", create)
            self.assertIn(["apply", "-f", "-"], args)
            self.assertFalse((base / "INJECTED").exists())
            process_env["CREATE_RC"] = "9"
            result = subprocess.run(["bash", "-c", script], cwd=tmp,
                                    env=process_env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 9, result.stderr)

    def test_settle_gate_fails_closed_on_cli_errors_and_empty_operators(self):
        tasks = yaml.safe_load((ROLES / "verify/tasks/cluster.yml").read_text())
        task = next(t for t in tasks if t["name"] == "Wait for the cluster to settle")
        env = Environment(undefined=StrictUndefined)
        env.filters["quote"] = shlex.quote
        with tempfile.TemporaryDirectory() as tmp:
            bindir = Path(tmp) / "bin ' $(touch INJECTED)"
            bindir.mkdir()
            fake = bindir / "oc"
            fake.write_text("#!/bin/bash\n"
                            'if [ "$2" = clusteroperators ]; then\n'
                            '  printf "%s" "$OPERATORS"; exit "$OPERATORS_RC"\n'
                            'fi\n'
                            'printf "%s" "$VERSION"; exit "$VERSION_RC"\n')
            fake.chmod(0o755)
            script = env.from_string(task["ansible.builtin.shell"]).render(install_bin_dir=str(bindir))
            healthy = "etcd 4.22 True False False 1h\n"
            for operators, op_rc, version, cv_rc, success in [
                    (healthy, 0, "True", 0, True),
                    (healthy, 7, "True", 0, False),
                    ("", 0, "True", 0, False),
                    (healthy, 0, "True", 8, False),
                    (healthy, 0, "False", 0, False),
                    ("etcd 4.22 False True True 1h\n", 0, "True", 0, False)]:
                result = subprocess.run(["bash", "-c", script], cwd=tmp, capture_output=True,
                                        env=dict(os.environ, OPERATORS=operators, OPERATORS_RC=str(op_rc),
                                                 VERSION=version, VERSION_RC=str(cv_rc)))
                self.assertEqual(result.returncode == 0, success, result.stderr)
            self.assertFalse((Path(tmp) / "INJECTED").exists())

    def test_ram_measure_rejects_arithmetic_source_and_quotes_tokens(self):
        tasks = yaml.safe_load((ROLES / "host_prep/tasks/main.yml").read_text())
        task = next(t for t in tasks if t["name"] == "Measure guest RAM already committed by running lab VMs")
        env = Environment(undefined=StrictUndefined)
        env.filters["quote"] = shlex.quote
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "virsh"
            fake.write_text("#!/bin/bash\nprintf 'running\\n'\n")
            fake.chmod(0o755)
            for specs, expected in [("m1=8 m2=016", "24"),
                                    ("m1=0", "0"),
                                    ("m1=$(touch${IFS}INJECTED)", None),
                                    ("m1=x[0$(touch${IFS}INJECTED)]", None)]:
                script = env.from_string(task["ansible.builtin.shell"]).render(
                    host_prep_node_mem_specs=specs, libvirt_uri="qemu:///system")
                result = subprocess.run(["bash", "-c", script], cwd=tmp, text=True, capture_output=True,
                                        env=dict(os.environ, PATH=tmp + ":" + os.environ["PATH"]))
                self.assertEqual(result.returncode == 0, expected is not None, result.stderr)
                if expected is not None:
                    self.assertEqual(result.stdout.strip(), expected)
                self.assertFalse((Path(tmp) / "INJECTED").exists())

    def test_ntp_cleanup_belongs_to_network_layer(self):
        tasks = yaml.safe_load((ROLES / "teardown/tasks/main.yml").read_text())
        task = next(t for t in tasks if t["name"] == "Remove the owned lab NTP relay permission")
        self.assertEqual(task["tags"], "network")
        self.assertEqual(task["ansible.builtin.blockinfile"]["marker"], "# {mark} DR-LAB NTP RELAY")
        self.assertEqual(task["ansible.builtin.blockinfile"]["state"], "absent")


if __name__ == "__main__":
    unittest.main()
