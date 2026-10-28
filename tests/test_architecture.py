"""Native architecture profiles and generated libvirt definitions."""
from pathlib import Path
import json
import unittest
import xml.etree.ElementTree as ET

from jinja2 import Environment, StrictUndefined
import yaml

ROOT = Path(__file__).resolve().parents[1]
COLLECTION = ROOT / 'ansible_collections/shanemcd/dr_lab'


class ArchitectureTests(unittest.TestCase):
    def test_domains_use_native_machine_and_keep_hardware_virtualization(self):
        profiles = yaml.safe_load((ROOT / 'inventory/group_vars/all/architecture.yml').read_text())['lab_arch_profiles']
        env = Environment(undefined=StrictUndefined)
        env.filters['bool'] = bool
        env.filters['to_uuid'] = lambda value: '00000000-0000-0000-0000-000000000001'
        env.filters['human_to_bytes'] = lambda value: 8589934592
        template = env.from_string((COLLECTION / 'roles/vms/templates/domain.xml.j2').read_text())
        for arch, machine, guest_arch in [('x86_64', 'q35', 'amd64'), ('aarch64', 'virt', 'arm64')]:
            with self.subTest(arch=arch):
                profile = profiles[arch]
                self.assertEqual(profile['kubevirt_arch'], guest_arch)
                xml = ET.fromstring(template.render(
                    lab_arch=arch, lab_arch_profile=profile,
                    node=dict(name='test-master', ram='8G', vcpu=2, data_disk=''),
                    libvirt_runtime_dir='/tmp/dr-lab', libvirt_probe=True,
                    qemu_binary_path='/usr/libexec/qemu-kvm', vms_master_iso_name='install.iso'))
                self.assertEqual(xml.attrib['type'], 'kvm')
                self.assertEqual(xml.find('os/type').attrib, dict(arch=arch, machine=machine))
                self.assertEqual(xml.find('cpu').attrib['mode'], 'host-passthrough')
                self.assertEqual(xml.find('os').attrib['firmware'], 'efi')

    def test_release_pins_cover_both_profiles(self):
        versions = yaml.safe_load((ROOT / 'inventory/group_vars/all/versions.yml').read_text())
        pins = versions['release_pins'][versions['ocp_version']]
        self.assertEqual(set(pins), {'x86_64', 'aarch64'})
        for arch in pins:
            for artifact in ('installer', 'client', 'iso'):
                self.assertRegex(pins[arch][artifact], r'^[0-9a-f]{64}$')
        self.assertNotEqual(pins['x86_64'], pins['aarch64'])

    def test_cpu_overcommit_is_explicit_and_preserves_headroom(self):
        tasks = yaml.safe_load((COLLECTION / 'roles/host_prep/tasks/main.yml').read_text())
        task = next(t for t in tasks if t['name'] == 'Assert CPU capacity')
        expressions = task['ansible.builtin.assert']['that']
        env = Environment(undefined=StrictUndefined)
        def accepts(cpus, ratio):
            context = dict(ansible_facts={'processor_vcpus': cpus},
                           host_prep_required_vcpu=140, host_prep_cpu_headroom=4,
                           host_prep_cpu_overcommit_ratio=ratio)
            return all(env.compile_expression(expr)(**context) for expr in expressions)
        self.assertFalse(accepts(64, 1.0))
        self.assertTrue(accepts(64, 3.0))
        self.assertFalse(accepts(4, 100.0))
        self.assertFalse(accepts(160, 0.5))
        self.assertTrue(accepts(144, 1.0))
        self.assertFalse(accepts(143, 1.0))

    def test_node_kvm_gate_rejects_missing_and_zero_capacity(self):
        tasks = yaml.safe_load((COLLECTION / 'roles/virtualization/tasks/cluster.yml').read_text())
        task = next(t for t in tasks if t['name'] == 'Require allocatable KVM on every managed node')
        env = Environment(undefined=StrictUndefined)
        env.filters['from_json'] = json.loads
        from ansible.plugins.filter.core import regex_search
        env.filters['regex_search'] = regex_search
        evaluate = env.compile_expression(task['until'])
        for capacity, expected in [(None, False), ('0', False), ('1', True), ('1000', True),
                                   ('1k', True), ('2Mi', True), ('0k', False),
                                   ('-1', False), ('garbage', False), ('100m', False)]:
            allocatable = {} if capacity is None else {'devices.kubevirt.io/kvm': capacity}
            result = dict(rc=0, stdout=json.dumps({'status': {'allocatable': allocatable}}))
            self.assertEqual(evaluate(virtualization_node_kvm=result), expected)
        self.assertFalse(evaluate(virtualization_node_kvm=dict(rc=1, stdout='')))

    def test_native_configuration_gate_rejects_software_emulation(self):
        tasks = yaml.safe_load((COLLECTION / 'roles/virtualization/tasks/cluster.yml').read_text())
        task = next(t for t in tasks if t['name'] == 'Require native KubeVirt execution configuration')
        env = Environment(undefined=StrictUndefined)
        env.filters['from_json'] = json.loads
        env.filters['bool'] = bool
        evaluate = env.compile_expression(task['until'])
        for spec, expected in [({}, True),
                               ({'configuration': {'developerConfiguration': {'useEmulation': False}}}, True),
                               ({'configuration': {'developerConfiguration': {'useEmulation': True}}}, False)]:
            result = dict(rc=0, stdout=json.dumps({'items': [{'spec': spec}]}))
            self.assertEqual(evaluate(virtualization_native_observed=result), expected)
        self.assertFalse(evaluate(virtualization_native_observed=dict(rc=0, stdout='{"items": []}')))
        self.assertFalse(evaluate(virtualization_native_observed=dict(rc=1, stdout='')))

    def test_preflight_rejects_unknown_cross_arch_and_mismatched_artifacts(self):
        tasks = yaml.safe_load((COLLECTION / 'roles/workspace/tasks/main.yml').read_text())
        task = next(t for t in tasks if t['name'] == 'Require a supported native architecture')
        profiles = yaml.safe_load((ROOT / 'inventory/group_vars/all/architecture.yml').read_text())['lab_arch_profiles']
        env = Environment(undefined=StrictUndefined)
        expressions = [env.compile_expression(e) for e in task['ansible.builtin.assert']['that']]
        for host, arch, artifact, expected in [
                ('x86_64', 'x86_64', 'x86_64', True),
                ('aarch64', 'aarch64', 'aarch64', True),
                ('x86_64', 'aarch64', 'aarch64', False),
                ('aarch64', 'x86_64', 'x86_64', False),
                ('x86_64', 'x86_64', 'aarch64', False),
                ('s390x', 's390x', 's390x', False)]:
            context = dict(lab_host_arch=host, lab_arch=arch, ocp_arch=artifact, lab_arch_profiles=profiles)
            self.assertEqual(all(e(**context) for e in expressions), expected)

    def test_nested_preflight_and_hardware_requirement(self):
        tasks = yaml.safe_load((COLLECTION / 'roles/host_prep/tasks/virtualization.yml').read_text())
        env = Environment(undefined=StrictUndefined)
        env.tests['search'] = lambda value, pattern: __import__('re').search(pattern, value) is not None
        from ansible.plugins.filter.core import to_bool
        env.filters['bool'] = to_bool
        nested = next(t for t in tasks if t['name'] == 'Require x86 nested virtualization')
        self.assertEqual(nested['when'], "lab_arch == 'x86_64'")
        check = env.compile_expression(nested['ansible.builtin.assert']['that'][0])
        for output, expected in [('/sys/module/kvm_intel/parameters/nested Y', True),
                                 ('/sys/module/kvm_amd/parameters/nested 1', True),
                                 ('/sys/module/kvm_intel/parameters/nested N', False),
                                 ('/sys/module/kvm_amd/parameters/nested 0', False),
                                 ('/sys/module/kvm_amd/parameters/nested 10', False),
                                 ('/sys/module/kvm_intel/parameters/nested Yellow', False),
                                 ('/sys/module/kvm_intel/parameters/nested N\n'
                                  '/sys/module/kvm_amd/parameters/nested 1', True), ('', False)]:
            self.assertEqual(check(host_prep_nested={'stdout': output}), expected)
        native = next(t for t in tasks if t['name'] == 'Require hardware virtualization for DR acceptance')
        self.assertNotIn('when', native)  # ARM must not escape the no-emulation rule.
        check = env.compile_expression(native['ansible.builtin.assert']['that'][0])
        for value, expected in [(False, True), ('false', True), (True, False), ('true', False)]:
            self.assertEqual(check(virtualization_use_emulation=value), expected)

    def test_emulation_is_not_default(self):
        config = yaml.safe_load((ROOT / 'inventory/group_vars/all/virtualization.yml').read_text())
        self.assertIs(config['virtualization_use_emulation'], False)


if __name__ == '__main__':
    unittest.main()
