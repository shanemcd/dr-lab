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

A full teardown followed by a **single untagged infrastructure deployment**
passed on 2026-10-28: `ok=756 changed=220 failed=0 rescued=0 ignored=0`.
This includes live cluster, storage, overlay, authenticated TLS S3, regional-DR
policy/peering, and final clock checks, with no manual recovery or stage retry.
See [rebuild validation](docs/rebuild-validation.md) for scope and evidence.
Running-VM execution and actual failover remain outstanding; infrastructure
success does not satisfy those acceptance criteria.

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

## Hub storage / DR console

The prerequisites stage enables `odf-multicluster-console` while preserving
existing console plugins. After refreshing the hub console, use **Fleet
Management → Data Services → Disaster recovery**, or open
`/multicloud/data-services/disaster-recovery` on the hub console.
To reconcile only this setting on an existing lab:

```bash
ansible-playbook shanemcd.dr_lab.11_dr_prerequisites --tags dr-console
```

The plugin's **Storage system** navigation additionally requires ACM Observability
and administrator access. This lab does not currently instantiate a
`MultiClusterObservability` resource or its metrics backend; enabling the console
plugin alone does not supply the storage topology/metrics view.

## License and provenance

[GPL-3.0-or-later](LICENSE). The collection follows conventions ported from
[cxl-lab](https://github.com/shanemcd/cxl-lab), also GPL-licensed. Registry
credentials, OpenShift installation assets and third-party collections are not
included; obtain dependencies and subscriptions separately as required.

Design references:
- [Regional DR](docs/regional-dr-design.md)
- [Standard compact-cluster storage](docs/compact-storage-design.md)
- [Hardware execution blocker](docs/hardware-blocker.md)
