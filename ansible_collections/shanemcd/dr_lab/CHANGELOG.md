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
- Document the historical ARM nested-virtualization/emulation execution blocker;
  current ARM running-guest recovery remains unvalidated.
- Add native x86_64/aarch64 platform profiles, release pins, capacity/nesting
  preflight, isolated pinned controller tools and maintained public guides.
- Add optional PVC-backed running-VM provisioning and initial protection.
  Demonstrate native x86_64 relocation, physically isolated failover and
  two-marker return with manual Velero metadata-import assistance. Unattended
  restore compatibility and maximum ongoing-write RPO remain unestablished;
  see the root `docs/current-validation.md` and `docs/compatibility.md`.
- Harden scoped shell boundaries, ownership checks before per-node VM staging,
  read-only teardown-path validation and generated-credential Git exclusions.
  These guards do not prove filesystem ownership or eliminate deletion races.
  Separate halted diagnostics remain outside the main pipeline and cannot
  substitute for running-guest acceptance.

## 0.3.0

ACM layer (08_acm, teardown --tags acm): multicluster-engine on the hub,
spoke import via auto-import secrets, work-manager + cluster-proxy add-ons.

## 0.2.0

OpenShift Virtualization layer (07_virtualization, teardown --tags virtualization).

## 0.1.0

Initial release: three-SNO bootstrap-in-place lab (host prep, artifacts,
network, ignition, VMs, cluster install, teardown, verify).
