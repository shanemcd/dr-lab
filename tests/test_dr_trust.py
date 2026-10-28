"""Exercise the actual Ansible CA-union expression and manifest offline."""
import pathlib
import subprocess
import tempfile
import unittest

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[1]
TASKS = ROOT / 'ansible_collections/shanemcd/dr_lab/roles/dr_prerequisites/tasks/trust-cluster.yml'


class TrustTests(unittest.TestCase):
    def test_union_preserves_custom_ca_and_is_idempotent(self):
        tasks = yaml.safe_load(TASKS.read_text())
        union = next(t for t in tasks if t['name'].startswith('Build a stable'))
        manifest = next(t for t in tasks if t['name'].startswith('Install the merged'))
        custom = '-----BEGIN CERTIFICATE-----\nCUSTOM\n-----END CERTIFICATE-----'
        primary = '-----BEGIN CERTIFICATE-----\nPRIMARY\n-----END CERTIFICATE-----'
        secondary = '-----BEGIN CERTIFICATE-----\nSECONDARY\n-----END CERTIFICATE-----'
        expected = '\n'.join([custom, primary, secondary])
        play = [{
            'name': 'Offline test of the deployment CA template',
            'hosts': 'localhost', 'gather_facts': False,
            'vars': {
                'dr_existing_ca_pem': custom + '\n' + primary,
                'dr_ingress_ca_results': {'results': [{'stdout': primary}, {'stdout': secondary}]},
                'dr_trust_bundle_name': 'dr-lab-regional-dr-ca',
                'expected_bundle': expected,
            },
            'tasks': [
                union,
                {'ansible.builtin.debug': {'var': 'dr_combined_ca_pem'}},
                {'ansible.builtin.assert': {'that': ['dr_combined_ca_pem == expected_bundle']}},
                {'ansible.builtin.set_fact': {
                    'rendered_manifest': manifest['ansible.builtin.command']['stdin'],
                    'dr_existing_ca_pem': '{{ dr_combined_ca_pem }}',
                }},
                union,
                {'ansible.builtin.assert': {'that': [
                    'dr_combined_ca_pem == expected_bundle',
                    "(rendered_manifest | from_yaml).data['ca-bundle.crt'] | trim == expected_bundle",
                    "(rendered_manifest | from_yaml).metadata.namespace == 'openshift-config'",
                ]}},
            ],
        }]
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / 'trust-test.yml'
            path.write_text(yaml.safe_dump(play))
            result = subprocess.run(
                ['ansible-playbook', '-i', 'localhost,', '-c', 'local', str(path)],
                cwd=ROOT, capture_output=True, text=True, timeout=40,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
