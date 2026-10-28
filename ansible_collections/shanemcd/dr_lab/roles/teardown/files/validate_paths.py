"""Read-only configuration guard, not an ownership check or race-free deletion API."""
import json
import os
import re


def inside(path, parent):
    return path != parent and os.path.commonpath([path, parent]) == parent


def validate(config):
    paths = config['paths']
    home = os.path.normpath(config['home'])
    if not os.path.isabs(home) or home == '/':
        raise ValueError('lab_user_home must be an absolute non-root directory')
    # Reject symlink components, including dangling links, and ambiguous spellings.
    for key, path in paths.items():
        if (not isinstance(path, str) or not os.path.isabs(path)
                or path != os.path.normpath(path) or path.startswith('//')
                or os.path.realpath(path) != path):
            raise ValueError(f'{key}: require canonical absolute path without symlink components')
    assets = paths['vm_assets_dir']
    install = paths['install_base_dir']
    # Dedicated workspace trees may live beneath HOME or these data roots.
    for key in ('vm_assets_dir', 'install_base_dir'):
        path = paths[key]
        roots = (home, '/srv', '/mnt', '/data', '/opt')
        if path == home or inside(home, path) or not any(inside(path, root) for root in roots):
            raise ValueError(f'{key}: require dedicated directory beneath HOME, /srv, /mnt, /data or /opt')
        for protected in config['protected']:
            protected = os.path.realpath(protected)
            if path == protected or inside(protected, path):
                raise ValueError(f'{key}: deletion would contain a protected path')
    for key in ('vm_ignition_dir', 'vm_run_dir', 'vm_logs_dir',
                'vm_images_dir', 'artifacts_downloads_dir'):
        if not inside(paths[key], assets):
            raise ValueError(f'{key}: must be strictly beneath vm_assets_dir')
    runtime = paths['libvirt_runtime_dir']
    if not inside(runtime, '/var/lib/libvirt/images'):
        raise ValueError('libvirt_runtime_dir: require dedicated child of /var/lib/libvirt/images')
    lb = paths['loadbalancer_state_dir']
    if not inside(lb, '/etc/dr-lab'):
        raise ValueError('loadbalancer_state_dir: require dedicated child of /etc/dr-lab')
    roots = (assets, install, runtime, lb)
    for i, left in enumerate(roots):
        for right in roots[i + 1:]:
            if left == right or inside(left, right) or inside(right, left):
                raise ValueError('workspace, install, runtime and load-balancer trees must not overlap')
    children = [paths[key] for key in ('vm_ignition_dir', 'vm_run_dir',
                'vm_logs_dir', 'vm_images_dir', 'artifacts_downloads_dir')]
    for i, left in enumerate(children):
        for right in children[i + 1:]:
            if left == right or inside(left, right) or inside(right, left):
                raise ValueError('independently removed workspace subtrees must not overlap')
    for name in config['names']:
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', name):
            raise ValueError('resource filenames must be simple names without path separators')


if __name__ == '__main__':
    validate(json.loads(os.environ['DR_TEARDOWN_PATHS']))
    print('Teardown path configuration validated (no files changed)')
