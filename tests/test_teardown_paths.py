"""Read-only teardown guards; never execute the destructive playbook."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / 'ansible_collections/shanemcd/dr_lab/roles/teardown'
SPEC = importlib.util.spec_from_file_location('validate_paths', ROLE / 'files/validate_paths.py')
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)


class TeardownPathTests(unittest.TestCase):
    def config(self, base):
        assets = str(base / 'assets')
        return {'home': str(base), 'protected': [str(base / '.ssh'), str(ROOT)],
                'paths': {'vm_assets_dir': assets, 'install_base_dir': str(base / 'install'),
                          'libvirt_runtime_dir': '/var/lib/libvirt/images/dr-lab',
                          'loadbalancer_state_dir': '/etc/dr-lab/loadbalancer',
                          **{key: assets + '/' + sub for key, sub in (
                              ('vm_ignition_dir', 'ignition'), ('vm_run_dir', 'run'),
                              ('vm_logs_dir', 'logs'), ('vm_images_dir', 'images'),
                              ('artifacts_downloads_dir', 'artifacts/downloads'))}},
                'names': ['dr-primary-m1', 'rhcos-install.iso', '99-dr-lab.conf']}

    def test_safe_layouts_and_absent_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = self.config(Path(tmp))
            GUARD.validate(config)
            config['paths']['install_base_dir'] = '/srv/dedicated-dr-install'
            GUARD.validate(config)
            self.assertFalse((Path(tmp) / 'assets').exists())

    def test_dangerous_paths_and_overlaps(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = self.config(Path(tmp))
            bad = [('vm_assets_dir', p) for p in ('/', tmp, '/etc', '/root', '/var',
                    '/srv', '/var/lib/libvirt/images', '/srv/../srv/lab', '//srv/lab')]
            bad += [('install_base_dir', config['paths']['vm_assets_dir'] + '/install'),
                    ('vm_ignition_dir', tmp), ('vm_run_dir', config['paths']['vm_logs_dir']),
                    ('libvirt_runtime_dir', '/var/lib/libvirt/images'),
                    ('loadbalancer_state_dir', '/etc'),
                    ('install_base_dir', str(ROOT.parent))]
            for key, path in bad:
                with self.subTest(key=key, path=path):
                    candidate = copy.deepcopy(config)
                    candidate['paths'][key] = path
                    with self.assertRaises(ValueError):
                        GUARD.validate(candidate)
            for name in ('../escape', '.', '..', '/etc', 'x/y', 'x\ny'):
                candidate = copy.deepcopy(config)
                candidate['names'] = [name]
                with self.subTest(name=name), self.assertRaises(ValueError):
                    GUARD.validate(candidate)

    def test_symlink_ancestors_including_dangling(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            config = self.config(base)
            (base / 'assets').symlink_to(base / 'missing', target_is_directory=True)
            with self.assertRaises(ValueError):
                GUARD.validate(config)
            (base / 'assets').unlink()
            (base / 'assets').mkdir()
            (base / 'assets' / 'artifacts').symlink_to(base, target_is_directory=True)
            with self.assertRaises(ValueError):
                GUARD.validate(config)

    def test_guard_is_first_always_and_check_mode_read_only(self):
        task = yaml.safe_load((ROLE / 'tasks/main.yml').read_text())[0]
        self.assertEqual(task['tags'], 'always')
        self.assertFalse(task['check_mode'])
        self.assertFalse(task['changed_when'])
        self.assertIn('DR_TEARDOWN_PATHS', task['environment'])
        self.assertEqual(task['ansible.builtin.command']['argv'][:2], ['python3', '-c'])


if __name__ == '__main__':
    unittest.main()
