# Validation and acceptance

A successful Ansible run is not proof of disaster recovery. Validate the following
layers separately, and retain timestamps and sanitized command results for each.
Historical ARM infrastructure results do not establish portability or VM recovery.

## Offline checks

From the repository root:

```sh
python3 -m unittest discover -s tests -v
ansible-galaxy collection install -r requirements.yml
ansible-playbook shanemcd.dr_lab.site --syntax-check
```

Unit tests check selected rendering and orchestration invariants. Syntax checks
require the external collections; neither check contacts or validates a cluster.

## Deployment acceptance

1. Host preflight passes: supported native architecture, KVM, nested virtualization,
   adequate memory and disk, usable firmware, and nonoverlapping lab networks.
2. All three clusters install. Nodes, cluster operators, and machine configuration
   pools are healthy. No pending or indiscriminately approved CSRs remain.
3. OpenShift Virtualization starts a real guest on both managed clusters. A halted
   VM object or an emulation configuration is not evidence of guest execution.
4. ACM imports both clusters; ODF has healthy replicated storage on each site.
5. Submariner connectivity and cross-site S3 access pass with certificate checking.
6. Ramen controllers, DRCluster, DRPolicy, OADP and the VM recipe reconcile without
   errors. Object and volume replication checkpoints are present and current.

## Planned relocation

Use a PVC-backed running VM with a guest-visible sequence number and timestamp
written and flushed to its persistent disk. Enroll the VM and PVC in protection.
Wait for a recoverable checkpoint, request relocation, and verify source shutdown,
replication completion, destination Running/Ready, and guest disk contents. Confirm
that exactly one writable copy and one running guest exist. A phase transition in
DRPlacementControl alone is insufficient.

## Unplanned failover

Record the most recent acknowledged write and protected checkpoint. Isolate the
source site before promotion using a verified fencing mechanism appropriate to the
deployment. Do not manually promote a mirror while its source can still write.
Request failover and verify destination VM Running/Ready, readable guest data, and
single-writer safety. Record:

- failure/isolation time;
- latest checkpoint and guest sequence recovered (observed data loss / RPO);
- recovery-ready and successful guest-read times (observed RTO);
- DRPC, VolumeReplicationGroup, storage and VM status on both sites;
- the isolation method, its verification, and any manual intervention.

This single-host topology models cluster/site failure, not host-failure resilience.
Destroying the physical host loses both simulated sites.

## Failback and evidence hygiene

Restore connectivity only when split-brain cannot occur. Reestablish replication,
wait for a fresh checkpoint, relocate back, and verify the same guest data checks.
Document failed checks as failures rather than relaxing safety or readiness gates.
Never publish pull secrets, kubeconfigs, tokens, guest keys, or S3 credentials.

## Current portability baseline

The initial offline baseline was 20 tests on Ansible Core 2.16.16/Jinja2 3.1.6.
The current supported controller environment uses the pinned dependencies in
`requirements-controller.txt`; 46 unit tests and site/teardown syntax checking pass with
Ansible Core 2.19.14. Live x86_64 infrastructure, guest execution and manually
assisted recovery evidence are recorded in [current validation](current-validation.md).
Do not confuse those scoped results with full acceptance: Ramen/Velero metadata
restore requires manual import and unattended reproducibility is unproven.
Both the original marker and a separate post-recovery-write marker survived the
assisted return; maximum ongoing-write RPO remains unmeasured.
