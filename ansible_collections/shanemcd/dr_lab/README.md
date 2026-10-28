# shanemcd.dr_lab

Ansible collection for the **test-only** OpenShift Virtualization regional DR
lab in this repository. Native x86_64 and aarch64 profiles are available, subject
to nested virtualization requirements. Ansible Core 2.19+ is required; the pinned
controller baseline is in `requirements-controller.txt` at the repository root.

Start with [getting started](../../../docs/getting-started.md),
[platforms](../../../docs/platforms.md), and
[validation criteria](../../../docs/validation.md). Run from the repository root
so that `ansible.cfg`, inventory and the local collection resolve consistently.

## Entrypoints

Invoke with `ansible-playbook shanemcd.dr_lab.<name> -e @local.yml`.

| Playbook | Purpose |
| --- | --- |
| `site` | All infrastructure stages and verification; not a running-VM DR test |
| `core` | Host through core cluster installation and verification |
| `01_host_prep` | Capacity, hardware, credentials, packages and time relay |
| `02_artifacts` | Checksum-pinned tools and RHCOS ISO |
| `03_network` | Libvirt network and DNS |
| `04_ignition` | Per-cluster installer inputs, lab SSH key and node ignition |
| `05_snos` | Persistent guests and load balancer (includes compact masters) |
| `06_install` | Installation, bootstrap completion and guarded bootstrap cleanup |
| `07_virtualization` | OpenShift Virtualization |
| `08_acm` | ACM hub and cluster imports |
| `09_storage` | ODF and local block devices |
| `10_submariner` | Overlay and connectivity checks |
| `11_dr_prerequisites` | GitOps/OADP/trust and DR console |
| `12_regional_dr` | Regional DR operators, peering and policy |
| `verify` | Core cluster and time verification |
| `sync_time` | Reconcile time configuration |
| `probe_overlay` | Diagnostic cross-site connectivity checks |
| `provision_running_vm` | One-time PVC-backed native guest fixture; refuses existing state |
| `protect_running_vm` | Initial protection of that existing guest after durable marker creation |
| `probe_halted_vm` | Diagnostic protection without guest execution |
| `relocate_halted_vm` | Diagnostic halted workload relocation, not failover proof |
| `teardown` | **Destructive** reverse-layer cleanup with ownership guards |

Numbered stages depend on earlier stages; they are not independent installers.
See the playbooks themselves for exact role ordering. Preserve the same overrides
across every stage. Do not reset installer state underneath running clusters.

## Configuration and installation state

The repository's `inventory/group_vars/all/` is the configuration reference.
Seven persistent guests comprise one hub SNO and two three-master compact sites;
two bootstrap guests are temporary. Network, disk and CPU sizing details are in
the root [overview](../../../README.md).

Installation inputs, generated SSH keys, kubeconfigs and runtime reports stay
outside Git under workspace directories. Libvirt runtime disks are held under
`/var/lib/libvirt/images/dr-lab`. Secrets must never be included in bug reports.

## Validation scope

Infrastructure readiness, running-VM execution, protection, planned relocation,
fenced unplanned failover and failback are separate gates. Native x86_64 stages
01–12, PVC guest execution, physical-source-isolated failover and two-marker
return have passed with manual metadata-import assistance. ARM execution and
unattended restore compatibility remain unvalidated. See
[current evidence](../../../docs/current-validation.md) and the exact
[compatibility limitation](../../../docs/compatibility.md); infrastructure
readiness alone is not recovery proof.
Historical ARM results and limitations are documented in
[rebuild evidence](../../../docs/rebuild-validation.md),
[hardware limitations](../../../docs/hardware-blocker.md), and
[halted diagnostics](../../../docs/halted-vm-protection.md).

## License

GPL-3.0-or-later; see [LICENSE](../../../LICENSE). Conventions originate in
[cxl-lab](https://github.com/shanemcd/cxl-lab). External software licenses and
OpenShift subscription requirements apply separately.
