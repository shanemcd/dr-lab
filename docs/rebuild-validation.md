# Full infrastructure rebuild validation

## Attempt 1 — 2026-10-28, loop iteration 26

Status: **in progress**, not full DR acceptance.

Executed untagged `ansible-playbook shanemcd.dr_lab.teardown` from the repository
root. It passed with `ok=84 changed=33 unreachable=0 failed=0`.
After the 240-second fleet graceful-shutdown window, the existing teardown
fallback force-stopped `dr-primary-m1`, `dr-primary-m3`, `dr-recovery-m1`, and
`dr-recovery-m2`. All other guests stopped normally. This was destructive lab
removal, not a DR fencing or failover test.

Post-teardown checks found no libvirt domains or networks, no `/root/ocp-dr`
workspace, and none of the three per-cluster install directories. Current guest
root and data disks were removed. Eight legacy `dr-{primary,recovery}-osd[1-4].raw`
files remain in the runtime directory: these are not referenced by the current
inventory or domains. Their ownership needs further verification before removal;
this is not a claim that every historical disk file was cleaned up.

Launched exactly one untagged `ansible-playbook shanemcd.dr_lab.site` after those
checks. It must complete all infrastructure and add-on stages plus verification
without manual recovery before a one-shot infrastructure pass can be recorded.
No successful rebuild is claimed while it is active.

At 05:56 UTC (iteration 27), all seven steady nodes are Ready. The hub installer
completion and membership/schedulability gates passed. The primary installer
confirmed bootstrap completion, and the source role switched its load balancer
and removed that temporary domain with UUID guards. The run is waiting for
primary install completion; recovery bootstrap cleanup and all add-on stages
remain ahead. No manual cluster repair, stage restart, or operator patch was
applied. Hub disk-boot NTP was observed at Stratum 4 / Leap Normal.

At 06:28 UTC (iteration 28), the same invocation remains active. All three
installer completion and exact Ready-membership/schedulability gates passed;
both compact bootstrap domains were removed through the source ownership guards.
OpenShift Virtualization operator gates passed on both sites, followed by ACM
hub installation, spoke availability, and add-on availability gates. The run is
now installing primary storage: CephCluster reports Ready / HEALTH_OK, while
StorageCluster is still Progressing and NooBaa database initialization has begun.
Recovery storage and subsequent transport/DR/verification stages remain ahead.
No deployment restart, manual operator repair, or stage skipping was performed.
These are intermediate results, not a successful full-site recap or VM execution
claim; Ceph's vendor-default authentication caveats still apply.

Host-local logs (may contain credentials; retain privately):
- `/tmp/dr-full-teardown-26.log`, exit marker `/tmp/dr-full-teardown-26.rc` = 0.
- `/tmp/dr-full-site-26.log`, exit marker `/tmp/dr-full-site-26.rc` when finished.
- Earlier diagnostic logs and serial logs preserved under
  `/root/dr-evidence/pre-rebuild-26/` with restricted permissions.

The separate running-VM and unplanned-failover criteria remain unverified and
hardware-blocked as described in [hardware-blocker.md](hardware-blocker.md).
The halted-VM diagnostic is not included as a substitute in `site.yml`.
