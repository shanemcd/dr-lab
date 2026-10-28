# dr-lab

Ansible automation for a regional disaster-recovery lab on one Fedora aarch64
libvirt host. The current topology is **seven steady-state guests**: an ACM hub
SNO plus two real three-master compact OpenShift clusters, with dedicated local
ODF disks. Two temporary UPI bootstrap guests are removed after installer gates.
This replaces the original three-SNO prototype.

The [`shanemcd.dr_lab`](ansible_collections/shanemcd/dr_lab) collection provisions
OpenShift 4.22.16, OpenShift Virtualization, full ACM, standard replicated ODF,
Submariner, GitOps/OADP, and managed regional-DR peering/policy. The full pipeline
is `ansible_collections/shanemcd/dr_lab/playbooks/site.yml`; see the collection
[README](ansible_collections/shanemcd/dr_lab/README.md) and design documents for
inventory, prerequisites, capacity, credentials and individual stages.

## Verification status — not complete acceptance

The installed infrastructure passed live cluster, storage, overlay, authenticated
TLS S3 and regional-policy checks. This is **not** proof that the entire lab can
be torn down and redeployed in one shot, or that a running VM can fail over.
Those acceptance criteria remain outstanding.

This host cannot expose nested ARM virtualization. Stock ARM64 VM admission
requires `host-passthrough`, incompatible with the tested software-emulation
runtime. No admission/operator bypass is used. See the exact reproducer and
limits in [hardware-blocker.md](docs/hardware-blocker.md).

A separate [halted-VM diagnostic](docs/halted-vm-protection.md) exercises disk
replication, object capture and planned relocation without executing a guest.
It is deliberately **not** included as a substitute workload in `site.yml`.
Its cleanup and filesystem-security findings are documented, not counted as a
running-VM failover pass. No production-support claim is made for this nested
ARM64 lab.

Design references:
- [Regional DR](docs/regional-dr-design.md)
- [Standard compact-cluster storage](docs/compact-storage-design.md)
- [Hardware execution blocker](docs/hardware-blocker.md)
