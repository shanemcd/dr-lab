"""Install-time and upgrade NTP configuration must use the same safe source."""
import base64
from pathlib import Path
import unittest

import jinja2
import yaml

ROOT = Path(__file__).resolve().parents[1]
ROLES = ROOT / 'ansible_collections/shanemcd/dr_lab/roles'


class TimeSyncTests(unittest.TestCase):
    def test_shared_master_config_and_reversible_relay(self):
        env = jinja2.Environment(undefined=jinja2.StrictUndefined)
        env.filters['b64encode'] = lambda value: base64.b64encode(value.encode()).decode()
        config = 'server 192.168.126.1 iburst\ndriftfile /var/lib/chrony/drift\n'
        text = (ROLES / 'install_config/templates/lab-chrony-machineconfig.yaml.j2').read_text()
        mc = yaml.safe_load(env.from_string(text).render(lab_chrony_config=config))
        self.assertEqual(mc['metadata']['labels']['machineconfiguration.openshift.io/role'], 'master')
        file = mc['spec']['config']['storage']['files'][0]
        self.assertEqual(file['path'], '/etc/chrony.conf')
        self.assertEqual(base64.b64decode(file['contents']['source'].split(',')[1]).decode(), config)
        for flavor in ('compact', 'sno'):
            tasks = (ROLES / f'install_config/tasks/cluster-{flavor}.yml').read_text()
            self.assertLess(tasks.index('lab-chrony-machineconfig.yaml.j2'),
                            tasks.index('- name: Create ignition configs') if flavor == 'compact'
                            else tasks.index('- name: Create the single-node'))
        for role, task in [('host_prep', 'time.yml'), ('teardown', 'main.yml')]:
            self.assertIn('# {mark} DR-LAB NTP RELAY', (ROLES / role / 'tasks' / task).read_text())
        self.assertNotIn('local stratum', (ROLES / 'host_prep/tasks/time.yml').read_text())
        upgrade = (ROLES / 'install_config/tasks/time-sync.yml').read_text()
        self.assertIn('--request-timeout=20s', upgrade)
        self.assertLess(upgrade.index('install_config_time_pool.rc == 0'),
                        upgrade.index('(install_config_time_pool.stdout | from_json).status.updatedMachineCount'))
        verify = (ROLES / 'verify/tasks/time.yml').read_text()
        self.assertIn('StrictHostKeyChecking=accept-new', verify)
        self.assertIn("'Leap status     : Normal'", verify)
        self.assertIn('lab_gateway_ip', verify)
