# dr-lab

Build an experimental OpenShift Virtualization regional disaster-recovery lab on
one Linux KVM host. Ansible provisions an ACM hub and two three-node compact
OpenShift clusters, then configures ODF storage, Submariner, OADP/GitOps and Ramen
regional DR. Native **x86_64 and aarch64** profiles are provided.

**This is an experimental, single-host lab, not production DR.** Native x86_64
running-VM recovery with physical source isolation and guest-data verification
has been demonstrated **with manual metadata-import assistance**. Unattended
recovery compatibility and maximum ongoing-write RPO are not established; the
single physical host remains a shared failure domain.

## Start here

- [Getting started](docs/getting-started.md): prerequisites, installation and stages.
- [Configuration](docs/configuration.md): coupled settings and fixed design boundaries.
- [Host platforms](docs/platforms.md): architecture profiles and nested KVM limits.
- [Operations](docs/operations.md): monitoring, troubleshooting, resuming and cleanup.
- [Current evidence](docs/current-validation.md): live portability deployment progress.
- [Validation](docs/validation.md): running-VM, relocation, failover and failback criteria.
- [Collection reference](ansible_collections/shanemcd/dr_lab/README.md): entrypoints.
- [Storage design](docs/compact-storage-design.md) and [regional DR design](docs/regional-dr-design.md).

## Default topology

| Cluster | Purpose | Resources |
| --- | --- | --- |
| `dr-hub` | Single-node OpenShift / ACM | 12 vCPU, 40 GiB RAM, 160 GiB root |
| `dr-primary` | Three schedulable masters / ODF / VMs | Each: 20 vCPU, 40 GiB RAM, 120 GiB root + 120 GiB ODF disk |
| `dr-recovery` | Same as primary | Same as primary |

Two temporary bootstrap guests add 8 vCPU, 32 GiB RAM and 120 GiB disk during
installation. Plan for **140 guest vCPU, 312 GiB RAM and 1,720 GiB nominal disk**
plus host headroom, artifact downloads and growth. CPU overcommit is opt-in;
memory and disk checks remain enforced. Defaults are in `inventory/group_vars/all/`.

## Validation status

- Offline: 46 tests, production-profile Ansible lint, scoped YAML lint and
  site/teardown syntax checks pass with the pinned controller/dev dependencies.
- x86_64: stages 01–12 passed, including three-cluster core, native
  virtualization, storage, transport and regional-DR readiness.
- ARM: a historical infrastructure rebuild passed, but its host lacked nested
  virtualization. That result does not validate running VMs or current changes.
- Live PVC-backed guest execution, planned relocation, physically fenced
  failover and planned return preserved the original guest marker. A separate
  post-recovery marker also survived return to the initial primary. Each recovery
  required manual Velero metadata import; unattended reproducibility is
  **not established**. See
  [current evidence and limitations](docs/current-validation.md).

Historical findings are retained in [ARM rebuild evidence](docs/rebuild-validation.md),
[ARM hardware limitations](docs/hardware-blocker.md), and
[halted-VM diagnostics](docs/halted-vm-protection.md). These are references, not
instructions to weaken readiness or safety checks.

## License

[GPL-3.0-or-later](LICENSE). The collection follows conventions from
[cxl-lab](https://github.com/shanemcd/cxl-lab), also GPL-licensed. OpenShift
credentials, subscriptions, installation assets and third-party dependencies are
not included. Obtain required access and licenses separately.
