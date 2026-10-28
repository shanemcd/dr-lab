"""Offline regression coverage for both ignition delivery paths."""
import base64
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from jinja2 import Environment, StrictUndefined

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'ansible_collections/shanemcd/dr_lab/roles/install_config/templates/ignition-node-merge.py.j2'


class IgnitionTests(unittest.TestCase):
    def test_node_wrapper_and_idempotency(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            script = work / 'merge.py'
            script.write_text(Environment(undefined=StrictUndefined).from_string(TEMPLATE.read_text()).render(
                bip_installation_disk='/dev/vda', base_domain='ocp.lab',
                install_config_nm_connection_id='lab', install_config_nm_connection_file='lab.nmconnection',
            ))
            source = work / 'master.ign'
            source.write_text(json.dumps({'ignition': {'version': '3.4.0', 'config': {
                'merge': [{'source': 'https://api-int.example:22623/config/master'}]}}}))
            hosts = work / 'hosts'
            hosts.write_text('192.168.126.12 api.dr-primary.ocp.lab\n')
            installed, wrapper, live = [work / name for name in ('installed.ign', 'wrapper.ign', 'live.ign')]

            def run(*args):
                return subprocess.check_output(['python3', str(script), *map(str, args)], text=True).strip()

            identity = ['dr-primary-m1', '192.168.126.13', '24', '192.168.126.1',
                        '52:54:00:0d:0d:0d', '192.168.126.1', hosts]
            self.assertEqual(run('node', source, installed, *identity), 'MERGED')
            target = json.loads(installed.read_text())
            self.assertEqual(target['ignition'], json.loads(source.read_text())['ignition'])
            files = {entry['path']: entry for entry in target['storage']['files']}
            hostname = files['/etc/hostname']['contents']['source'].split(',', 1)[1]
            self.assertEqual(base64.b64decode(hostname), b'dr-primary-m1\n')
            self.assertEqual(run('node', source, installed, *identity), 'UNCHANGED')
            self.assertEqual(run('wrapper', installed, wrapper), 'MERGED')
            config = json.loads(wrapper.read_text())
            embedded = config['storage']['files'][0]['contents']['source'].split(',', 1)[1]
            self.assertEqual(json.loads(base64.b64decode(embedded)), target)
            unit = config['systemd']['units'][0]['contents']
            self.assertIn('install /dev/vda --copy-network', unit)
            self.assertEqual(run('wrapper', installed, wrapper), 'UNCHANGED')
            self.assertEqual(run('node', wrapper, live, *identity), 'MERGED')
            self.assertEqual(len(json.loads(live.read_text())['storage']['files']), 4)


if __name__ == '__main__':
    unittest.main()
