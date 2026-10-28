"""Provisioning fixture safety/architecture contracts; not live guest evidence."""
import base64
import json
from pathlib import Path
import unittest

from jinja2 import Environment, StrictUndefined
import yaml

ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / 'ansible_collections/shanemcd/dr_lab/roles/running_vm'


class RunningVMTests(unittest.TestCase):
    def test_native_persistent_guest_and_no_recreated_marker(self):
        config = yaml.safe_load((ROOT / 'inventory/group_vars/all/workload.yml').read_text())
        profiles = yaml.safe_load((ROOT / 'inventory/group_vars/all/architecture.yml').read_text())['lab_arch_profiles']
        env = Environment(undefined=StrictUndefined)
        env.filters['to_json'] = json.dumps
        env.filters['b64decode'] = lambda s: base64.b64decode(s).decode()
        template = env.from_string((ROLE / 'templates/workload.yml.j2').read_text())
        for arch in profiles:
            with self.subTest(arch=arch):
                pin = config['workload_image_pins'][arch]
                self.assertRegex(pin, '^sha256:[a-f0-9]{64}$')
                values = dict(config, lab_arch_profile=profiles[arch],
                              running_vm_public_key={'content': base64.b64encode(b'ssh-ed25519 TEST').decode()})
                values['workload_image'] = 'docker://quay.io/containerdisks/fedora@' + pin
                dv, vm = list(yaml.safe_load_all(template.render(**values)))
                self.assertEqual(dv['spec']['source']['registry']['pullMethod'], 'node')
                spec = vm['spec']['template']['spec']
                self.assertEqual(spec['architecture'], profiles[arch]['kubevirt_arch'])
                self.assertEqual(vm['spec']['runStrategy'], 'Always')
                self.assertEqual(spec['domain']['cpu']['model'], 'host-passthrough')
                self.assertIn('persistentVolumeClaim', spec['volumes'][0])
                cloud = yaml.safe_load(spec['volumes'][1]['cloudInitNoCloud']['userData'])
                self.assertNotIn('write_files', cloud)
                self.assertFalse(cloud['ssh_pwauth'])
                self.assertEqual(cloud['users'][0]['ssh_authorized_keys'], ['ssh-ed25519 TEST'])
                self.assertEqual(cloud['runcmd'], [['systemctl', 'enable', '--now', 'qemu-guest-agent']])

    def test_reseeding_guard_precedes_mutations(self):
        tasks = yaml.safe_load((ROLE / 'tasks/main.yml').read_text())
        self.assertIn('BOTH sites', tasks[0]['name'])
        self.assertIn('ansible.builtin.assert', tasks[1])
        env = Environment(undefined=StrictUndefined)
        check = env.compile_expression(tasks[1]['ansible.builtin.assert']['that'][0])
        self.assertTrue(check(running_vm_existing={'results': [{'stdout': ''}, {'stdout': ''}]}))
        for a, b in [('namespace/test', ''), ('', 'namespace/test')]:
            self.assertFalse(check(running_vm_existing={'results': [{'stdout': a}, {'stdout': b}]}))
        env.filters['from_json'] = json.loads
        env.tests['contains'] = lambda collection, value: value in collection
        protected = env.compile_expression(tasks[3]['ansible.builtin.assert']['that'][0])
        for items, allowed in [([], True), ([{'spec': {'protectedNamespaces': ['fixture']}}], False)]:
            self.assertEqual(protected(running_vm_controls={'stdout': json.dumps({'items': items})},
                                       workload_namespace='fixture'), allowed)

    def test_initial_protection_is_separate_and_guarded(self):
        collection = ROOT / 'ansible_collections/shanemcd/dr_lab'
        play = yaml.safe_load((collection / 'playbooks/protect_running_vm.yml').read_text())[0]
        tasks = play['tasks']
        mutations = [i for i, task in enumerate(tasks) if 'kubernetes.core.k8s' in task]
        self.assertEqual(len(mutations), 1)
        self.assertTrue(all('ansible.builtin.command' not in t or
                            t['ansible.builtin.command']['argv'][1] in ['get', '--request-timeout=20s']
                            for t in tasks))
        guards = [t for t in tasks[:mutations[0]] if 'ansible.builtin.assert' in t]
        self.assertEqual(len(guards), 6)
        env = Environment(undefined=StrictUndefined)
        env.filters['from_json'] = json.loads
        env.tests['contains'] = lambda collection, value: value in collection
        checks = tasks[1]['ansible.builtin.assert']['that']
        for controls, allowed in [([], True),
                                  ([{'metadata': {'name': 'other'}, 'spec': {'protectedNamespaces': ['dr-running-vm']}}], False),
                                  ([{'metadata': {'name': 'fedora-dr'}, 'spec': {}}], False)]:
            values = dict(running_vm_controls={'stdout': json.dumps({'items': controls})},
                          workload_namespace='dr-running-vm', workload_name='fedora-dr')
            self.assertEqual(all(env.compile_expression(c)(**values) for c in checks), allowed)
        placement, drpc = list(yaml.safe_load_all(env.from_string(
            (collection / 'templates/running-vm-protection.yml.j2').read_text()).render(
                workload_name='fedora-dr', workload_namespace='dr-running-vm',
                acm_spokes=['primary', 'secondary'], regional_dr_policy_name='policy')))
        self.assertEqual(placement['metadata']['namespace'], 'openshift-dr-ops')
        self.assertTrue(drpc['spec']['retainNamespaceSCCAcrossPeers'])
        self.assertEqual(drpc['spec']['kubeObjectProtection']['recipeRef']['name'], 'vm-recipe')
        self.assertNotIn('action', drpc['spec'])
        self.assertEqual(drpc['spec']['protectedNamespaces'], ['dr-running-vm'])
        gate = tasks[-1]['until']
        for field in ['lastGroupSyncTime', 'lastKubeObjectProtectionTime', 'observedGeneration', 'Protected']:
            self.assertIn(field, gate)


if __name__ == '__main__':
    unittest.main()
