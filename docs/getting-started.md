# Getting started

## Prerequisites

Use a dedicated Red Hat-family Linux host with systemd and native x86_64 or
aarch64 virtualization. Review [platform requirements](platforms.md) and the
[default topology](../README.md) before running anything. Nested hardware
virtualization must work inside the OpenShift guests; ARM Altra machines without
nesting cannot run the required workload. Do not substitute software emulation.

You need privileged access, working NTP and Internet DNS, access to the OpenShift
mirror and image registries, a valid OpenShift pull secret, and repositories
providing the packages in `inventory/group_vars/all/host.yml`. The host Python
needs the distribution's `python3-kubernetes` package (for example from EPEL on
RHEL); enable the appropriate trusted repositories first. Host preparation
installs packages and configures services including time synchronization and
firewalld. Inspect those tasks before using a host with other workloads.

## Install controller dependencies

Run from the cloned repository root. Python 3.11+ and Ansible Core 2.19.x are the
controller baseline; an isolated environment avoids replacing system Ansible.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-controller.txt
ansible-galaxy collection install -r requirements.yml -p .
python -m unittest discover -s tests -v
ansible-playbook shanemcd.dr_lab.site --syntax-check
# Optional maintained lint checks (do not execute deployment):
python -m pip install -r requirements-dev.txt
ansible-lint --offline
yamllint inventory ansible_collections/shanemcd/dr_lab requirements.yml
```

The inventory defaults to this local host. `ansible.cfg` resolves collections
from the repository root. Remote-host provisioning is not currently validated.
Do not assume every path/lookup works remotely without testing it.

## Configure your lab

Review the [configuration contract](configuration.md) for coupled settings and
fixed design boundaries, then the taxonomy files under `inventory/group_vars/all/`:

| File | Settings |
| --- | --- |
| `architecture.yml` | Native machine, console, emulator and firmware packages |
| `versions.yml` | Release, download locations, per-architecture checksum pins |
| `topology.yml` | Hub, three-master sites, bootstraps and resources |
| `network.yml` | Bridge, lab subnet, DNS/base domain and host connectivity |
| `paths.yml` | Workspace account and installation/runtime directories |
| `secrets.yml` | Pull-secret and generated SSH key paths (not secret values) |
| `workload.yml` | Optional running-VM fixture image, PVC and namespace |
| `storage.yml` | ODF provisioning and local block disks |
| `acm.yml`, `virtualization.yml` | Cluster management and guest runtime |
| `submariner.yml`, `dr.yml`, `regional_dr.yml` | Overlay, prerequisites and protection policy |

Keep deployment overrides in an untracked `local.yml` and pass `-e @local.yml`
to **every** stage, including verification. For example:

```yaml
# local.yml (gitignored)
install_pull_secret_path: /secure/path/pull-secret.txt
# Optional: accept up to 3 guest vCPUs per host logical CPU after host headroom.
# This increases CPU contention and is not a performance guarantee.
host_prep_cpu_overcommit_ratio: 3.0
```

Default CPU overcommit is 1.0 and headroom is four host logical CPUs. The default
140-vCPU installation therefore requires 144 logical CPUs without overcommit;
a 64-thread host needs an explicit ratio of at least 140 / (64 - 4). Memory
requires 312 + 12 GiB and disk requires 1,720 + 30 GiB plus operational growth.
Changing CPU sizing inside guests may prevent storage/operator scheduling;
CPU overcommit on the host does not change Kubernetes allocatable resources.

For a small test deployment you can reduce `compact_master_data_disk`, but
`storage_device_request` must also fit the resulting local disk (for example
`100G` disks and `99Gi` requests). This reduces usable replicated capacity;
it is not a production ODF sizing recommendation. Keep root disks and host
headroom intact, and allow space for artifacts, snapshots and actual disk growth.
Never resize an existing populated OSD by changing these variables.

Copy your pull secret outside Git and restrict it to mode 0600. The default is
`<workspace-account-home>/pull-secret.txt`. The workspace account is the invoking
user, or `SUDO_USER` when invoked under sudo; set `lab_user` to override. A
separate lab SSH key is generated automatically during ignition preparation;
you do not need to supply your personal SSH key.

The default private lab subnet is `192.168.126.0/24` and base domain is `ocp.lab`.
Ensure lab, pod and service networks do not overlap existing routes or VPNs.
Do not point public DNS at this test domain. Configure resolvers as appropriate
for your environment and preserve management-network access.

## Deploy

Use privilege escalation (`-K` if sudo requires a password). Keep the same
inventory, workspace account, configuration and release throughout a deployment.

```sh
ansible-playbook shanemcd.dr_lab.site -e @local.yml
```

`site` installs the full infrastructure and runs its component gates. It does
**not** currently prove live workload failover. To inspect or resume stages:

```sh
ansible-playbook shanemcd.dr_lab.core -e @local.yml
ansible-playbook shanemcd.dr_lab.09_storage -e @local.yml
ansible-playbook shanemcd.dr_lab.10_submariner -e @local.yml
ansible-playbook shanemcd.dr_lab.11_dr_prerequisites -e @local.yml
ansible-playbook shanemcd.dr_lab.12_regional_dr -e @local.yml
ansible-playbook shanemcd.dr_lab.verify -e @local.yml
```

Operator channels are rolling, not exact-version locks. Review the observed
[recovery compatibility limitation](compatibility.md): the tested combination
needed manual metadata-import assistance, even after infrastructure gates passed.
No unattended recovery or vendor-certified matrix is implied.

Inspect failure evidence before resuming. Ignition has a 12-hour freshness window;
do not reuse stale/partial installer assets or regenerate credentials under
running nodes. Existing-state guards may require deliberate lab teardown/rebuild.

## Access, validation and cleanup

Per-cluster installer credentials are in `~/ocp-install-dr/<cluster>/auth/` for
the workspace account. Console URLs are
`https://console-openshift-console.apps.<cluster>.ocp.lab`. Do not publish
kubeconfigs, passwords, ignition, S3 keys or raw logs containing credentials.

The DR console is **Fleet Management → Data Services → Disaster recovery**.
The additional Storage system metrics view requires ACM Observability and a
backend; this lab does not provision those simply by enabling a console plugin.

Follow [validation](validation.md) before claiming recovery works. The separate
`probe_halted_vm` and `relocate_halted_vm` playbooks are diagnostics only.

Teardown is destructive: review its guarded ownership checks and scope first.
It removes lab resources, not a general-purpose reset of your host.

```sh
ansible-playbook shanemcd.dr_lab.teardown -e @local.yml
```
