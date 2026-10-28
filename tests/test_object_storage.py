"""Exercise the actual object-storage gate with synthetic (never live) keys."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

import yaml


class ObjectStorageTests(unittest.TestCase):
    def test_bucket_gate_rejects_missing_endpoints_or_credentials(self):
        role = Path(__file__).resolve().parents[1] / "ansible_collections/shanemcd/dr_lab/roles/storage"
        tasks = yaml.safe_load((role / "tasks/object-smoke.yml").read_text())
        task = tasks[-1]
        self.assertTrue(task["no_log"])
        self.assertFalse(task["changed_when"])
        script = task["ansible.builtin.shell"].split("python3 -c '", 1)[1].rsplit("'", 1)[0]
        config = {"BUCKET_NAME": "test", "BUCKET_HOST": "s3.example.test", "BUCKET_PORT": "443"}
        secret = {"AWS_ACCESS_KEY_ID": "dummy", "AWS_SECRET_ACCESS_KEY": "dummy"}

        def check(cm, credentials, success):
            result = subprocess.run(
                [sys.executable, "-c", script],
                input=json.dumps({"items": [
                    {"kind": "ConfigMap", "data": cm}, {"kind": "Secret", "data": credentials},
                ]}), text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode == 0, success)
            self.assertEqual(result.stdout, "")
            self.assertNotIn("dummy", result.stderr)

        check(config, secret, True)
        for key in config:
            check({k: v for k, v in config.items() if k != key}, secret, False)
        for key in secret:
            check(config, {k: v for k, v in secret.items() if k != key}, False)
        check({}, {}, False)


if __name__ == "__main__":
    unittest.main()
