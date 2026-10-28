"""Exercise the real pre-ODF gate; PV affinity terms are OR alternatives."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

from jinja2 import Environment
import yaml


class StoragePVTests(unittest.TestCase):
    def test_requires_one_local_block_disk_per_host(self):
        root = Path(__file__).resolve().parents[1]
        tasks = yaml.safe_load((root / "ansible_collections/shanemcd/dr_lab/roles/storage/tasks/cluster.yml").read_text())
        task = next(t for t in tasks if t["name"] == "Require one local block PV per selected node")
        script = task["ansible.builtin.shell"].split("python3 -c '", 1)[1].rsplit("'", 1)[0]
        env = Environment()
        env.filters["to_json"] = json.dumps
        script = env.from_string(script).render(
            storage_lso_storageclass="localblock",
            storage_members=[{"name": h} for h in ["m1", "m2", "m3"]],
        )

        def term(*hosts):
            return {"matchExpressions": [{"key": "kubernetes.io/hostname", "operator": "In", "values": list(hosts)}]}

        def pv(host):
            return {"spec": {"storageClassName": "localblock", "volumeMode": "Block",
                             "local": {"path": "/mnt/local-storage/disk"},
                             "nodeAffinity": {"required": {"nodeSelectorTerms": [term(host)]}}},
                    "status": {"phase": "Available"}}

        good = [pv(h) for h in ["m1", "m2", "m3"]]

        def check(items, success):
            result = subprocess.run([sys.executable, "-c", script],
                                    input=json.dumps({"items": items}), text=True,
                                    capture_output=True, check=False)
            self.assertEqual(result.returncode == 0, success, result.stderr)

        check(good, True)
        bound = copy.deepcopy(good)
        bound[0]["status"]["phase"] = "Bound"
        check(bound, True)
        check(good[:2], False)
        check(good + [pv("m4")], False)
        check([pv("m1"), pv("m1"), pv("m3")], False)
        check([pv("m1"), pv("m2"), pv("foreign")], False)
        for alternatives in [[term("m1", "m2", "m3")], [term("m1"), {}],
                             [term("m1"), term("m2")], []]:
            bad = copy.deepcopy(good)
            bad[0]["spec"]["nodeAffinity"]["required"]["nodeSelectorTerms"] = alternatives
            check(bad, False)
        for field, value in [("volumeMode", "Filesystem"), ("local", {}),
                             ("storageClassName", "foreign")]:
            bad = copy.deepcopy(good)
            bad[0]["spec"][field] = value
            check(bad, False)


if __name__ == "__main__":
    unittest.main()
