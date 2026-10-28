import base64
import contextlib
import io
import json
import pathlib
import runpy
import unittest
from unittest.mock import patch

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / (
    'ansible_collections/shanemcd/dr_lab/roles/submariner/files/s3-probe.py')


class S3ProbeTests(unittest.TestCase):
    def run_probe(self, corrupt=False):
        payload = {'secret': {k: base64.b64encode(v.encode()).decode() for k, v in {
            'AWS_ACCESS_KEY_ID': 'test-access', 'AWS_SECRET_ACCESS_KEY': 'test-secret'}.items()},
            'ca': base64.b64encode(b'public-ca').decode(), 'host': 's3.remote.example',
            'config': {'BUCKET_NAME': 'smoke'}}
        calls, state = [], {}

        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def read(self):
                return state.get('response', b'')

        class Opener:
            def open(inner, req, timeout):
                calls.append(req)
                if req.method == 'PUT':
                    state['body'] = req.data
                state['response'] = (b'corrupt' if corrupt else state['body']) if req.method == 'GET' else b''
                return Response()

        stdout = io.StringIO()
        with patch('sys.stdin', io.StringIO(json.dumps(payload))), \
                patch('ssl.create_default_context') as tls, \
                patch('urllib.request.build_opener', return_value=Opener()), \
                contextlib.redirect_stdout(stdout):
            if corrupt:
                with self.assertRaisesRegex(AssertionError, 'Remote S3 content mismatch'):
                    runpy.run_path(str(SCRIPT))
            else:
                runpy.run_path(str(SCRIPT))
                self.assertIn('PASS authenticated TLS', stdout.getvalue())
            tls.assert_called_once_with(cadata='public-ca')
        self.assertEqual([r.method for r in calls], ['PUT', 'GET', 'DELETE'])
        for r in calls:
            self.assertTrue(r.full_url.startswith('https://s3.remote.example/smoke/dr-lab-probe-'))
            auth = r.get_header('Authorization')
            self.assertIn('AWS4-HMAC-SHA256 Credential=test-access/', auth)
            self.assertIn('SignedHeaders=host;x-amz-content-sha256;x-amz-date', auth)
        self.assertNotIn('test-secret', stdout.getvalue())

    def test_signed_put_get_delete_and_verified_tls(self):
        self.run_probe()

    def test_cleanup_even_when_data_verification_fails(self):
        self.run_probe(corrupt=True)


if __name__ == '__main__':
    unittest.main()
