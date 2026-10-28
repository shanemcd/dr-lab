"""Authenticated cross-site S3 smoke: stdlib only, TLS verification mandatory.
Payload arrives on stdin via oc exec, not oc/Python command arguments.
This script creates no credential files; Ansible transport is managed separately.
"""
import base64
import datetime
import hashlib
import hmac
import json
import ssl
import sys
import urllib.parse
import urllib.request
import uuid

p = json.load(sys.stdin)
access = base64.b64decode(p['secret']['AWS_ACCESS_KEY_ID']).decode()
secret = base64.b64decode(p['secret']['AWS_SECRET_ACCESS_KEY']).decode()
ca = base64.b64decode(p['ca']).decode()
context = ssl.create_default_context(cadata=ca)
opener = urllib.request.build_opener(
    urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=context))
host = p['host']
assert '/' not in host and ':' not in host
bucket = p['config']['BUCKET_NAME']
key = 'dr-lab-probe-' + str(uuid.uuid4())
path = urllib.parse.quote('/' + bucket + '/' + key, safe='/~')
region = p['config'].get('BUCKET_REGION', 'noobaa')
body = ('authenticated-dr-s3:' + key).encode()


def sign(key_bytes, text):
    return hmac.new(key_bytes, text.encode(), hashlib.sha256).digest()


def request(method, data=b''):
    now = datetime.datetime.now(datetime.timezone.utc)
    timestamp, day = now.strftime('%Y%m%dT%H%M%SZ'), now.strftime('%Y%m%d')
    digest = hashlib.sha256(data).hexdigest()
    names = 'host;x-amz-content-sha256;x-amz-date'
    headers = f'host:{host}\nx-amz-content-sha256:{digest}\nx-amz-date:{timestamp}\n'
    canonical = '\n'.join([method, path, '', headers, names, digest])
    scope = f'{day}/{region}/s3/aws4_request'
    to_sign = '\n'.join(['AWS4-HMAC-SHA256', timestamp, scope,
                         hashlib.sha256(canonical.encode()).hexdigest()])
    signing_key = sign(sign(sign(sign(('AWS4' + secret).encode(), day), region), 's3'), 'aws4_request')
    signature = hmac.new(signing_key, to_sign.encode(), hashlib.sha256).hexdigest()
    auth = f'AWS4-HMAC-SHA256 Credential={access}/{scope}, SignedHeaders={names}, Signature={signature}'
    req = urllib.request.Request('https://' + host + path, data=data if method == 'PUT' else None,
                                 method=method, headers={'Host': host, 'X-Amz-Date': timestamp,
                                 'X-Amz-Content-SHA256': digest, 'Authorization': auth})
    with opener.open(req, timeout=30) as response:
        assert 200 <= response.status < 300
        return response.read()


written = False
try:
    request('PUT', body)
    written = True
    assert request('GET') == body, 'Remote S3 content mismatch'
finally:
    if written:
        request('DELETE')
print('PASS authenticated TLS S3 PUT/GET/DELETE via ' + host)
