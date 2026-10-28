# Changelog

## Unreleased

- Replace the three-SNO prototype with a hub SNO and two three-master compact
  sites, using temporary UPI bootstrap guests and ownership-guarded removal.
- Add standard three-node replicated ODF, Submariner with real cross-site probes,
  GitOps/OADP prerequisites, and managed regional-DR peering/policy.
- Include host-relayed time synchronization in fresh ignition and verify all
  seven guest clocks, with scoped core evidence and separate add-on gates.
- Validate a full teardown and single untagged infrastructure deployment on
  2026-10-28 (`ok=756 changed=220 failed=0 rescued=0 ignored=0`), without manual
  repair or stage retries. See the root `docs/rebuild-validation.md`.
- Document the ARM nested-virtualization/emulation execution blocker. Running-VM
  failover remains unverified; separate halted-VM diagnostics are not acceptance
  substitutes and are not included in the main pipeline.

## 0.3.0

ACM layer (08_acm, teardown --tags acm): multicluster-engine on the hub,
spoke import via auto-import secrets, work-manager + cluster-proxy add-ons.

## 0.2.0

OpenShift Virtualization layer (07_virtualization, teardown --tags virtualization).

## 0.1.0

Initial release: three-SNO bootstrap-in-place lab (host prep, artifacts,
network, ignition, VMs, cluster install, teardown, verify).
