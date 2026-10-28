import pathlib
import unittest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
ROLE = ROOT / 'ansible_collections/shanemcd/dr_lab/roles/regional_dr/tasks'


class RegionalDRTests(unittest.TestCase):
    def test_matches_shipped_datafoundation_console_flow(self):
        tasks = yaml.safe_load((ROLE / 'main.yml').read_text())
        facts = tasks[0]['ansible.builtin.set_fact']
        self.assertEqual(facts['regional_dr_peer_spec']['type'], 'async')
        self.assertIs(facts['regional_dr_peer_spec']['manageS3'], True)
        self.assertEqual(len(facts['regional_dr_peer_spec']['items']), 2)
        self.assertEqual(facts['regional_dr_policy_spec']['replicationClassSelector'], {})
        payload = next(t for t in tasks if 'ansible.builtin.command' in t)['ansible.builtin.command']['stdin']
        self.assertIn('kind: MirrorPeer', payload)
        self.assertIn('kind: DRPolicy', payload)
        self.assertNotIn('kind: DRCluster', payload)  # owned by orchestration
        immutable = (ROLE / 'immutable.yml').read_text()
        self.assertIn('Refusing to change immutable', immutable)
        self.assertIn('regional_dr_existing.stdout | length > 0', immutable)
        site = (ROLE / 'site.yml').read_text()
        self.assertIn("'equalto', 'Validated'", site)
        self.assertIn("regional_dr_peer_status.stdout == 'Peered'", site)
        self.assertNotIn('conditions[2]', site)

    def test_overlay_is_direct_and_bidirectional(self):
        role = ROLE.parent.parent / 'submariner/tasks'
        client = (role / 'probe-client.yml').read_text()
        server = (role / 'probe-server.yml').read_text()
        self.assertIn('ProxyHandler({})', client)
        self.assertIn('spec.clusterIP', client)
        self.assertIn('status.podIP', client)
        self.assertIn('hostNetwork: false', server)
        self.assertIn('runAsNonRoot: true', server)
        self.assertIn("rejectattr('metadata.deletionTimestamp', 'defined')", client)
        self.assertIn('loop: "{{ acm_spokes }}"', (role / 'probe.yml').read_text())


if __name__ == '__main__':
    unittest.main()
