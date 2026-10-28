# shanemcd.dr_lab

Ansible collection for a **test-only** regional disaster-recovery lab on a
Fedora aarch64 libvirt host, using distribution QEMU and edk2 firmware.
The current topology is an ACM hub SNO plus two three-master compact OpenShift
clusters: seven steady guests and two temporary UPI bootstrap guests.

Ported from [cxl-lab](https://github.com/shanemcd/cxl-lab) conventions:
numbered playbooks, taxonomy-driven group variables, checksum-pinned artifacts,
fresh-window ignition gating, and ownership-guarded teardown.

## Topology and capacity

| Cluster | Role | Domain | Addresses on 192.168.126.0/24 |
| --- | --- | --- | --- |
| `dr-hub` | SNO / ACM | `dr-hub.ocp.lab` | node `.11` |
| `dr-primary` | Three-master compact / ODF | `dr-primary.ocp.lab` | API/ingress VIP `.12`, nodes `.13`–`.15` |
| `dr-recovery` | Three-master compact / ODF | `dr-recovery.ocp.lab` | API/ingress VIP `.16`, nodes `.17`–`.19` |

- OpenShift **4.22.16 aarch64**, RHCOS `rhel-9` ISO, pinned checksums.
- Hub: 12 vCPU, 40 GiB RAM, 160 GiB root disk; bootstrap-in-place installation.
- Each spoke master: 20 vCPU, 40 GiB RAM, 120 GiB root + dedicated 120 GiB ODF disk.
- Each temporary bootstrap: 4 vCPU, 16 GiB RAM, 60 GiB disk; addresses `.21`/`.22`.
- Budget: 132 vCPU / 280 GiB RAM steady, 140 vCPU / 312 GiB with both bootstraps,
  plus host headroom. This was tested on a 160-core, 501 GiB host.
- Each cluster has distinct pod/service CIDRs. Dedicated host HAProxy serves
  compact-cluster API/MCS and ingress VIPs; libvirt supplies lab DNS/networking.
- Compact clusters use real UPI bootstrap completion before the playbook switches
  load-balancer backends and removes ownership-verified temporary domains.

Authoritative settings are in the repository's `inventory/group_vars/all/`.

## Usage

Run from the repository root. Review inventory, capacity, networking, package
changes and destructive teardown behavior before execution. Host preparation
requires privilege. Supply a valid registry pull secret as a mode-0600 file;
`install_pull_secret_path` defaults to `/root/pull-secret.txt`. Never commit it.

```bash
ansible-galaxy collection install -p . -r requirements.yml

# Full infrastructure: host, artifacts, network, load balancer, ignition, VMs,
# cluster installation, virtualization, ACM, storage, Submariner,
# GitOps/OADP prerequisites, regional DR, and final verification.
ansible-playbook shanemcd.dr_lab.site

# Core installation only, or individual numbered stages 01 through 12
ansible-playbook shanemcd.dr_lab.core
ansible-playbook shanemcd.dr_lab.09_storage
ansible-playbook shanemcd.dr_lab.10_submariner
ansible-playbook shanemcd.dr_lab.11_dr_prerequisites
ansible-playbook shanemcd.dr_lab.12_regional_dr

# Core-state and clock checks; add-on stages have their own gates
ansible-playbook shanemcd.dr_lab.verify

# DESTRUCTIVE: removes the lab using guarded reverse-layer teardown
ansible-playbook shanemcd.dr_lab.teardown
```

Consoles: `https://console-openshift-console.apps.<cluster>.ocp.lab`.
Kubeconfigs default to `~/ocp-install-dr/<cluster>/auth/kubeconfig`, resolved for
the workspace account; access credentials and runtime reports stay outside Git.
Ignition has a limited certificate window; stale or partial installation state
fails with teardown guidance rather than silently reusing invalid assets.

## Verified scope and limitations

A full teardown followed by a single untagged infrastructure deployment passed
on 2026-10-28: **756 ok, 220 changed, 0 failed, 0 rescued, 0 ignored**. This includes
storage provisioning, real cross-site HTTP/S3 probes, DR peering/policy, and final
cluster/clock gates, without manual recovery or stage retries.

**Running-VM execution and actual failover are not verified.** The tested Ampere
Altra host cannot expose nested KVM to its OpenShift guests. The tested stock
ARM64 emulation path also fails because admission requires a CPU mode that cannot
execute with TCG. Operator readiness is not a VM execution pass. Suitable hardware
is needed to finish acceptance; no production-support claim is made for this lab.

The separate halted-VM probe/relocation playbooks are diagnostics, not part of
`site.yml` and not substitutes for running-VM failover. Their historical source-PVC
cleanup failure remains documented. No TLS, admission, fencing, finalizer, or
SELinux bypass is used to turn an incomplete result into a pass.

Repository documentation:
- [Overview](../../../README.md)
- [Rebuild validation](../../../docs/rebuild-validation.md)
- [Compact storage design and Ceph authentication caveats](../../../docs/compact-storage-design.md)
- [Regional DR design](../../../docs/regional-dr-design.md)
- [VM execution blocker and remaining acceptance](../../../docs/hardware-blocker.md)
- [Historical halted-VM diagnostics](../../../docs/halted-vm-protection.md)

## License

GPL-3.0-or-later; see the repository's [LICENSE](../../../LICENSE).
