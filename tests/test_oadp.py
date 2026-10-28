"""Offline checks of actual OADP task expressions and manifests."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / 'ansible_collections/shanemcd/dr_lab/roles/dr_prerequisites/tasks'


class OadpTests(unittest.TestCase):
    def test_namespacing_group_safety_and_dpa(self):
        oadp = yaml.safe_load((TASKS / 'oadp.yml').read_text())
        operator = yaml.safe_load((TASKS / 'operator.yml').read_text())
        main = yaml.safe_load((TASKS / 'main.yml').read_text())
        oadp_index = next(i for i, t in enumerate(main) if t.get('ansible.builtin.include_tasks') == 'oadp.yml')
        orchestrator_index = next(i for i, t in enumerate(main) if 'Orchestrator and' in t['name'])
        self.assertLess(oadp_index, orchestrator_index)
        dpa_task = next(t for t in oadp if 'discovered-application' in t['name'])
        dpa = yaml.safe_load(dpa_task['ansible.builtin.command']['stdin'])
        self.assertEqual(dpa['metadata']['namespace'], 'openshift-adp')
        self.assertFalse(dpa['spec']['backupImages'])
        self.assertFalse(dpa['spec']['configuration']['nodeAgent']['enable'])
        self.assertEqual(dpa['spec']['configuration']['velero'], {
            'defaultPlugins': ['openshift', 'aws', 'kubevirt'], 'noDefaultBackupLocation': True,
        })
        guard = next(t for t in oadp if 'Refuse conflicting' in t['name'])
        tasks = []
        for groups, valid in [([], True), ([{'spec': {'targetNamespaces': ['openshift-adp']}}], True),
                              ([{'spec': {}}], False),
                              ([{'spec': {'targetNamespaces': ['other']}}], False),
                              ([{'spec': {}}, {'spec': {}}], False)]:
            tasks += [
                {'ansible.builtin.set_fact': {'dr_oadp_groups': {'stdout': json.dumps({'items': groups})}}},
                {**guard, 'ignore_errors': True, 'register': 'guard_result'},
                {'ansible.builtin.assert': {'that': [f'guard_result.failed == {not valid}']}},
            ]
        subscription = next(t for t in operator if 'Subscribe in' in t['name'])
        tasks += [
            {'ansible.builtin.set_fact': {'manifest': subscription['ansible.builtin.command']['stdin']}},
            {'ansible.builtin.assert': {'that': [
                "(manifest | from_yaml).metadata.namespace == 'openshift-operators'",
            ]}},
            {'ansible.builtin.set_fact': {'dr_operator_namespace': 'openshift-adp'}},
            {'ansible.builtin.set_fact': {'manifest': subscription['ansible.builtin.command']['stdin']}},
            {'ansible.builtin.assert': {'that': [
                "(manifest | from_yaml).metadata.namespace == 'openshift-adp'",
            ]}},
        ]
        play = [{'hosts': 'localhost', 'gather_facts': False, 'vars': {
            'dr_operator_package': 'redhat-oadp-operator', 'dr_operator_channel': 'stable',
        }, 'tasks': tasks}]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.yml'
            path.write_text(yaml.safe_dump(play))
            result = subprocess.run(['ansible-playbook', '-i', 'localhost,', '-c', 'local', str(path)],
                                    cwd=ROOT, capture_output=True, text=True, timeout=40)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
