# Halted VM diagnostic (not VM failover acceptance)

The host's ARM64 nested-KVM/emulation blocker remains as documented in
[hardware-blocker.md](hardware-blocker.md). This explicitly separate diagnostic
must not replace a running workload in `site.yml` or be counted as running-VM
failover.

Run from the repository root:

```sh
ansible-playbook ansible_collections/shanemcd/dr_lab/playbooks/probe_halted_vm.yml
```

It creates `dr-halted-probe/halted-marker` on the primary site: a **Halted** VM
and a filesystem RBD PVC containing a 64 MiB raw `disk.img`. There is no guest OS.
A restricted, non-root, tokenless helper writes and fsyncs a fixed marker at
1 MiB, verifies existing content rather than overwriting it, then is deleted
before protection. The hub DRPlacementControl uses Ramen's built-in `vm-recipe`
and a namespace-specific PVC/resource selector. Its dummy Placement has ACM
scheduling disabled so Ramen owns placement decisions.

The probe waits for current-generation `Protected=True`, a disk synchronization
timestamp, and an object-protection timestamp. `PeerReady=True` alone is not
sufficient: initialization can report that while `Available=False`. It refuses
to reseed if the existing diagnostic DRPC has an action or a different preferred
cluster. It leaves the protected application intact for subsequent recovery
verification; it does not delete protected PVCs or claim safe automatic cleanup.
Do not create a second DRPC selecting this PVC.

## Runtime findings, 2026-10-28

This exercise found two real gaps that infrastructure readiness had not exposed:

1. Full ACM on the hub does not imply spoke governance agents are installed.
   Without `governance-policy-framework` and `config-policy-controller`, Ramen's
   policies existed but S3 credentials never reached the spokes. Both agents are
   now inventory-managed through the ACM role. The normal policy controllers
   distributed the credentials; no secret was manually copied.
2. Proxy custom trust is not sufficient for Velero's dynamically generated BSLs.
   They failed with `tls: failed to verify certificate: x509: certificate signed
   by unknown authority`. ODF 4.22 guide section 4.16.1 step 3 explicitly requires
   base64 `caCertificates` on the hub Ramen ConfigMap's S3 profiles for self-signed
   ingress. The regional DR role now merges only that documented field, preserves
   all other generated configuration, and waits for normal operator propagation
   to both spokes. No BSL/Deployment patch, insecure TLS flag, or restart is used.

Live evidence:

- ACM reconcile: `/tmp/dr-acm-governance.log`, 23 ok / 4 changed / 0 failed;
  both governance agents Available on both sites and generated policies Compliant.
- Certificate configuration: `/tmp/dr-object-trust.log`, 28 ok / 1 changed /
  0 failed; both generated BSLs subsequently Available with CA certificates.
  Immediate `/tmp/dr-object-trust-rerun.log`: 27 ok / 0 changed / 0 failed.
- Halted protection: `/tmp/dr-halted-protection-rerun.log`, 8 ok / 3 changed /
  0 failed. Final guarded `/tmp/dr-halted-protection-guarded.log`: 10 ok /
  3 changed / 0 failed, including explicit timestamp and reseeding guards.
- Primary DRPC: Deployed / Completed / Protected=True, observed generation 2.
- Primary VRG: lastGroupSyncTime `2026-10-28T04:43:14Z`, 667648 sync bytes;
  object capture completed `2026-10-28T04:47:15Z`, startGeneration 3;
  ClusterDataProtected=True. Controller observed Velero Completed, zero warnings
  and zero errors. Transient capture errors recovered through normal reconciliation.

These facts prove a replication checkpoint and successful object capture, **not**
that recovery can restore and read the marker, not that a VM has executed, and
not that unplanned failover is fenced or split-brain-safe. Those remain separate
acceptance work, as does the full teardown and one-shot redeployment.
