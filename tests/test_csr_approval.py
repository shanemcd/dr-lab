"""Inventory-bound CSR policy tests; no cluster access required."""
import base64
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import runpy
import sys
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / (
    'ansible_collections/shanemcd/dr_lab/roles/cluster_install/files/approve-node-csrs.py')


class ApprovalTests(unittest.TestCase):
    def evaluate(self, username, signer, usages, subject, san='', conditions=None):
        approved = []
        csr = {'metadata': {'name': 'csr-test'}, 'spec': {
            'request': base64.b64encode(b'request').decode(), 'username': username,
            'signerName': signer, 'usages': usages}, 'status': {}}
        if conditions:
            csr['status']['conditions'] = conditions

        def output(args, **kwargs):
            if args[0] == 'openssl':
                return ('subject=' + subject) if '-subject' in args else (
                    'X509v3 Subject Alternative Name:\n    ' + san)
            if 'approve' in args:
                approved.append(args[-2])
                return 'approved'
            return json.dumps({'items': [csr]})

        with patch.object(sys, 'argv', [str(SCRIPT), 'oc', '{"dr-primary-m1":"192.168.126.13"}']), \
                patch('subprocess.check_output', side_effect=output), redirect_stdout(io.StringIO()):
            runpy.run_path(str(SCRIPT), run_name='__main__')
        return approved

    def test_client_identity_checks(self):
        args = ['system:serviceaccount:openshift-machine-config-operator:node-bootstrapper',
                'kubernetes.io/kube-apiserver-client-kubelet', ['digital signature', 'client auth'],
                'CN=system:node:dr-primary-m1,O=system:nodes']
        self.assertEqual(self.evaluate(*args), ['csr-test'])
        self.assertEqual(self.evaluate('untrusted', *args[1:]), [])
        args[-1] = 'CN=system:node:unrelated,O=system:nodes'
        self.assertEqual(self.evaluate(*args), [])

    def test_serving_san_checks(self):
        args = ['system:node:dr-primary-m1', 'kubernetes.io/kubelet-serving',
                ['digital signature', 'server auth'], 'CN=system:node:dr-primary-m1,O=system:nodes']
        self.assertEqual(self.evaluate(*args, 'DNS:dr-primary-m1, IP Address:192.168.126.13'), ['csr-test'])
        self.assertEqual(self.evaluate(*args, 'DNS:api.dr-primary.ocp.lab'), [])
        self.assertEqual(self.evaluate(*args, ''), [])
        self.assertEqual(self.evaluate(*args, 'DNS:dr-primary-m1', [{'type': 'Denied'}]), [])


if __name__ == '__main__':
    unittest.main()
