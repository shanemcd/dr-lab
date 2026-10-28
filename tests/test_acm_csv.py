"""Regression checks for subscription-scoped ACM CSV readiness."""
from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


class AcmCsvTests(unittest.TestCase):
    def test_wait_targets_subscription_csv_not_namespace_history(self):
        tasks = yaml.safe_load((ROOT / 'ansible_collections/shanemcd/dr_lab/roles/acm/tasks/main.yml').read_text())
        selected = next(t for t in tasks if t.get('register') == 'acm_csv_created')
        argv = selected['ansible.builtin.command']['argv']
        self.assertIn('subscription/{{ acm_package }}', argv)
        self.assertIn('jsonpath={.status.installedCSV}', argv)
        self.assertIn('acm_csv_created.rc == 0', selected['until'])
        ready = next(t for t in tasks if t['name'] == 'Wait for the operator CSV to report Succeeded')
        argv = ready['ansible.builtin.command']['argv']
        self.assertIn('csv/{{ acm_csv_created.stdout }}', argv)
        self.assertNotIn('--all', argv)
        self.assertIn('--for=jsonpath={.status.phase}=Succeeded', argv)


if __name__ == '__main__':
    unittest.main()
