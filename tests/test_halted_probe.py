"""Diagnostic safeguards: halted protection must not masquerade as VM execution."""
from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOKS = ROOT / 'ansible_collections/shanemcd/dr_lab/playbooks'


class HaltedProbeTests(unittest.TestCase):
    def test_governance_agents_required_for_operator_secret_distribution(self):
        inventory = yaml.safe_load((ROOT / 'inventory/group_vars/all/acm.yml').read_text())
        self.assertIn('governance-policy-framework', inventory['acm_spoke_addons'])
        self.assertIn('config-policy-controller', inventory['acm_spoke_addons'])

    def test_documented_profile_ca_preserves_operator_configuration(self):
        role = ROOT / 'ansible_collections/shanemcd/dr_lab/roles/regional_dr/tasks'
        tasks = yaml.safe_load((role / 'object-trust.yml').read_text())
        patch = next(t for t in tasks if t['name'] == 'Configure supported Ramen object-backup certificate trust')
        self.assertIn("combine({'s3StoreProfiles':", patch['vars']['regional_dr_object_updated'])
        self.assertIn('--type=merge', patch['ansible.builtin.command']['argv'])
        self.assertNotIn('insecure', (role / 'object-trust.yml').read_text().lower())
        wait = next(t for t in tasks if 'register' in t and t['register'] == 'regional_dr_object_spoke_config')
        self.assertIn('caCertificates', wait['until'])
        self.assertIn('b64encode', wait['until'])

    def test_probe_is_explicit_halted_diagnostic_with_real_protection_gate(self):
        play = yaml.safe_load((PLAYBOOKS / 'probe_halted_vm.yml').read_text())[0]
        tasks = play['tasks']
        create = next(t for t in tasks if t.get('register') == 'halted_apply')
        self.assertIn('runStrategy: Halted', create['ansible.builtin.command']['stdin'])
        placement = next(t for t in tasks if t.get('register') == 'halted_protect')
        manifest = placement['ansible.builtin.command']['stdin']
        self.assertIn('experimental-scheduling-disable', manifest)
        self.assertIn('name: vm-recipe', manifest)
        self.assertIn('retainNamespaceSCCAcrossPeers: true', manifest)
        retention = next(t for t in tasks if t['name'].startswith('Require supported namespace SCC'))
        self.assertIn('retainNamespaceSCCAcrossPeers', str(retention))
        wait = next(t for t in tasks if t.get('register') == 'halted_drpc')
        self.assertIn("'Protected'", wait['until'])
        self.assertIn('metadata.generation', wait['until'])
        self.assertNotIn("'PeerReady'", wait['until'])
        self.assertNotIn('probe_halted_vm', (PLAYBOOKS / 'site.yml').read_text())

    def test_relocation_is_guarded_planned_diagnostic_and_read_only(self):
        text = (PLAYBOOKS / 'relocate_halted_vm.yml').read_text()
        tasks = yaml.safe_load(text)[0]['tasks']
        patch = next(t for t in tasks if t['name'].startswith('Request planned relocation'))
        self.assertIn('/metadata/resourceVersion', str(patch))
        self.assertIn("'value': 'Relocate'", str(patch))
        self.assertNotIn("'value': 'Failover'", str(patch))
        guard = next(t for t in tasks if t.get('register') == 'halted_instances')
        self.assertIn("['items']", guard['failed_when'])
        demotion = next(t for t in tasks if t.get('register') == 'halted_demoting')
        self.assertIn("replicationState == 'secondary'", demotion['until'])
        cleanup = next(t for t in tasks if t.get('register') == 'halted_source_cleanup')
        self.assertIn('vm,pvc', cleanup['ansible.builtin.command']['argv'])
        self.assertNotIn('--all', str(cleanup))
        self.assertLess(tasks.index(demotion), tasks.index(cleanup))
        reader = next(t for t in tasks if t.get('register') == 'halted_reader_apply')
        self.assertIn('readOnly: true', reader['ansible.builtin.command']['stdin'])
        self.assertIn("open('/disk/disk.img', 'rb')", reader['ansible.builtin.command']['stdin'])
        self.assertNotIn('relocate_halted_vm', (PLAYBOOKS / 'site.yml').read_text())


if __name__ == '__main__':
    unittest.main()
