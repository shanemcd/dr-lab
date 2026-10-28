import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class SubmarinerTests(unittest.TestCase):
    def test_documented_namespace_not_generic_addon_default(self):
        text = (ROOT / 'ansible_collections/shanemcd/dr_lab/roles/submariner/tasks/spoke.yml').read_text()
        addon = text.split('kind: ManagedClusterAddOn', 1)[1]
        self.assertIn('installNamespace: submariner-operator', addon)
        self.assertNotIn('spec: {}', addon)
        self.assertIn('until: submariner_join.rc == 0', text)
        self.assertIn('until: submariner_addon.rc == 0', text)


if __name__ == '__main__':
    unittest.main()
