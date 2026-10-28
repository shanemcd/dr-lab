# Historical ARM infrastructure rebuild evidence

This report describes the previous aarch64 deployment on 2026-10-28, not the
current portability changes or x86_64 host. See [current evidence](current-validation.md)
for the new deployment. A successful infrastructure rebuild does **not** prove
running-VM execution or failover.

## Scope and result

One untagged `shanemcd.dr_lab.teardown` passed:

```text
lab-server : ok=84 changed=33 unreachable=0 failed=0
```

After the 240-second graceful-shutdown window, teardown force-stopped
`dr-primary-m1`, `dr-primary-m3`, `dr-recovery-m1` and `dr-recovery-m2`.
This was destructive cleanup, not DR fencing or failover. Post-cleanup checks
found no lab libvirt domains/network, workspace or cluster installation
directories. Eight legacy `dr-{primary,recovery}-osd[1-4].raw` files remained
unreferenced; ownership was not established, so they were not deleted. This was
not a claim that every historical disk was removed.

Exactly one untagged `shanemcd.dr_lab.site` invocation then passed, running from
approximately 05:20 to 07:09 UTC (1 hour 49 minutes):

```text
lab-server : ok=756 changed=220 unreachable=0 failed=0 skipped=42 rescued=0 ignored=0
```

Exit status was 0. No stage restart, manual cluster recovery, playbook retry,
operator patch or safety-gate skipping was used. Documentation-only edits did
not change executing automation. The then-current 20 offline tests also passed.

## Gates observed

- All three installers confirmed completion, expected membership and schedulable
  masters. All seven persistent nodes became Ready.
- Both compact bootstrap domains were removed after installer-confirmed
  bootstrap completion, using UUID ownership guards and load-balancer updates.
- OpenShift Virtualization CSV/HCO/deployment gates passed on both managed sites.
  These were operator gates, not evidence of a running guest.
- ACM hub, spoke availability and required add-ons passed.
- Both StorageClusters reached Ready; Ceph HEALTH_OK, dynamic RBD PVC binding,
  NooBaa readiness and dynamic bucket checks passed.
- Submariner connections, cross-site PodIP/ClusterIP application probes and
  authenticated remote S3 exchange with verified TLS passed.
- GitOps, OADP, cross-cluster trust, DR policy validation, managed operator
  rollout, StorageCluster peering and namespace mirroring health passed.
- Final core verification found seven domains running, OpenShift 4.22.16
  Available, 34/34 operators Available per cluster, all machine config pools
  Updated and all guest clocks synchronized through the lab relay.

Ceph's vendor-default authentication caveats still apply; HEALTH_OK is not proof
of AES256K-only client security. See [storage design](compact-storage-design.md).
Core verification reports were scoped to core state; separate add-on task logs
supplied the add-on evidence.

## Evidence retention and limits

The historical operator retained private invocation logs, exit markers and core
reports with local SHA256 checksums (directory mode 0700, files 0600). Those
records are local evidence, not third-party attestation, and are not included in
the repository. Do not expect the files to exist on a new host or publish raw
logs containing credentials.

The ARM host could not execute the required nested guest. Its separate halted
VM protection/recovery diagnostic was not included as a substitute in `site`.
See [hardware limitations](hardware-blocker.md) and
[halted diagnostics](halted-vm-protection.md). Running-VM relocation, fenced
failover, guest data verification and failback remained unproven.
