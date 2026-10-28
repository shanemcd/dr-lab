#!/usr/bin/env python3
"""Approve pending UPI node CSRs only for inventory identities.

The lab controls all bootstrap credentials. Inspect the signed request subject,
requester, signer, usages and serving SANs before granting certificates.
"""
import base64
import json
import subprocess
import sys

oc, nodes_json = sys.argv[1:]
nodes = json.loads(nodes_json)


def run(*args, **kwargs):
    return subprocess.check_output(args, text=True, **kwargs)


for csr in json.loads(run(oc, 'get', 'csr', '-o', 'json', '--request-timeout=15s'))['items']:
    if csr.get('status', {}).get('conditions') or csr.get('status', {}).get('certificate'):
        continue
    spec = csr['spec']
    request = base64.b64decode(spec['request'], validate=True)
    subject = run('openssl', 'req', '-noout', '-subject', '-nameopt', 'RFC2253', input=request.decode())
    subject = subject.strip().removeprefix('subject=').strip()
    usages = set(spec.get('usages', []))
    for name, ip in nodes.items():
        identity = 'system:node:' + name
        if subject not in (f'CN={identity},O=system:nodes', f'O=system:nodes,CN={identity}'):
            continue
        signer = spec.get('signerName')
        if signer == 'kubernetes.io/kube-apiserver-client-kubelet':
            if spec.get('username') != 'system:serviceaccount:openshift-machine-config-operator:node-bootstrapper':
                continue
            if usages not in ({'digital signature', 'key encipherment', 'client auth'},
                              {'digital signature', 'client auth'}):
                continue
        elif signer == 'kubernetes.io/kubelet-serving':
            if spec.get('username') != identity:
                continue
            if usages not in ({'digital signature', 'key encipherment', 'server auth'},
                              {'digital signature', 'server auth'}):
                continue
            text = run('openssl', 'req', '-noout', '-text', input=request.decode())
            lines = text.splitlines()
            san = next((lines[i + 1].strip() for i, line in enumerate(lines[:-1])
                        if 'X509v3 Subject Alternative Name:' in line), '')
            allowed = {'DNS:' + name, 'IP Address:' + ip}
            if not san or not set(san.split(', ')) <= allowed:
                continue
        else:
            continue
        print(run(oc, 'adm', 'certificate', 'approve', csr['metadata']['name'], '--request-timeout=15s').strip())
        break
