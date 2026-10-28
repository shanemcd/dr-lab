"""Offline ownership/query gates and optional teardown-layer selection."""
from pathlib import Path
import unittest

from jinja2 import Environment, StrictUndefined
import yaml

ROOT = Path(__file__).resolve().parents[1]
ROLES = ROOT / 'ansible_collections/shanemcd/dr_lab/roles'


class VmOwnershipTests(unittest.TestCase):
    def test_identity_precedes_all_runtime_mutations(self):
        tasks = yaml.safe_load((ROLES / 'vms/tasks/libvirt-node.yml').read_text())
        self.assertEqual([task['name'] for task in tasks[:3]], [
            'Query the defined domain inventory', 'Check whether this domain is defined',
            'Refuse to overwrite an unrelated same-name domain'])
        # Failed list is fatal by default; do not infer absence from query errors.
        self.assertNotIn('failed_when', tasks[0])
        self.assertEqual(tasks[0]['ansible.builtin.command']['argv'][-3:],
                         ['list', '--all', '--name'])
        env = Environment(undefined=StrictUndefined)
        query_fails = env.compile_expression(tasks[1]['failed_when'])
        for rc, names, expected in [(0, ['fixture'], False), (1, ['fixture'], True),
                                    (1, [], False), (0, [], False)]:
            self.assertEqual(query_fails(vms_domain_info={'rc': rc},
                                        node={'name': 'fixture'},
                                        vms_defined_domains={'stdout_lines': names}), expected)
        env.filters['to_uuid'] = lambda value: 'expected-uuid'
        belongs = env.compile_expression(tasks[2]['ansible.builtin.assert']['that'])
        self.assertTrue(belongs(node={'name': 'fixture'},
                                vms_domain_info={'stdout': 'UUID: expected-uuid'}))
        self.assertFalse(belongs(node={'name': 'fixture'},
                                 vms_domain_info={'stdout': 'UUID: unrelated-uuid'}))

    def test_in_cluster_uninstalls_are_explicit_and_before_vm_removal(self):
        tasks = yaml.safe_load((ROLES / 'teardown/tasks/main.yml').read_text())
        env = Environment(undefined=StrictUndefined)
        for name, tag in [('Remove the ACM layer', 'acm'),
                          ('Remove the OpenShift Virtualization layer', 'virtualization')]:
            task = next(t for t in tasks if t['name'] == name)
            self.assertEqual(task['tags'], tag)
            allowed = env.compile_expression(task['when'])
            self.assertTrue(allowed(ansible_run_tags=[tag]))
            self.assertFalse(allowed(ansible_run_tags=['all']))
            self.assertFalse(allowed(ansible_run_tags=['vms', tag]))


if __name__ == '__main__':
    unittest.main()
