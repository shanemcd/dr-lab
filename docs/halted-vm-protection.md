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

## Planned relocation diagnostic (iteration 25)

`playbooks/relocate_halted_vm.yml` is also separate from `site.yml`. It requires
both managed sites Available, no VMI in the diagnostic namespace on either site,
the exact diagnostic identity and current-generation protection. It requests
`action: Relocate` and changes `preferredCluster` using a resourceVersion-tested
JSON patch. It never requests unplanned failover or edits fencing/status.

ODF 4.22 section 4.11 limits automatic garbage collection to VM-owned resources.
The marker PVC is standalone, so after Ramen requests source demotion following
final sync, the diagnostic explicitly deletes only its labelled Halted VM and
PVC. It does not strip finalizers. Completion additionally requires current
source Secondary / target Primary, restored VM Halted, and a restricted read-only
reader verifying the marker. These checks do not prove running-VM failover.

The first live exercise found two additional gaps rather than passing:

- Ramen reached **Relocated / Completed**, source VRG Secondary and recovery VRG
  Primary, and restored a Halted VM plus Bound PVC. Source PVC deletion stayed
  Terminating with Ramen and VGR protection finalizers. The strict source cleanup
  gate timed out (`/tmp/dr-halted-relocation-cleanup.log`). `Protected=False`
  reports `No PVC on the secondary should match the label selector`. No finalizer
  was removed and no replication state was patched to hide this.
- A separately resumed recovery read (not a full-playbook pass) failed with
  `PermissionError: [Errno 13] Permission denied: '/disk/disk.img'`.
  Source namespace SCC groups/UID range were `1000900000/10000`, recovery
  `1000910000/10000`; SELinux MCS also differed. No root reader, custom SCC,
  permission rewrite, or SELinux bypass was used. The failed reader was removed.

The deployed DRPC API documents `retainNamespaceSCCAcrossPeers`: both DRPC and
RamenConfig must enable it **before** creating the secondary namespace. The hub
configuration already has it true; the initial diagnostic omitted the DRPC flag.
The protection playbook now explicitly enables it and verifies the hub flag.
An isolated second diagnostic uses distinct names/selectors (`dr-halted-probe-v2`,
`halted-marker-v2`); it cannot select the original PVC. The original failed
exercise is retained as evidence, not retroactively declared successful.

The corrected second exercise passed protection (`/tmp/dr-halted-v2-protection.log`,
12 ok / 4 changed / 0 failed); both namespaces have the same SCC UID/group range
`1000930000/10000` and SELinux MCS `s0:c31,c0`. Its full relocation play still
failed the strict source-PVC cleanup timeout (`/tmp/dr-halted-v2-relocation.log`).
After that process finished, only the recovery verification portion was resumed
with `--start-at-task 'Wait for the controller to finish planned relocation'`
and explicit `lab_user_home=/root`, namespace/name overrides. This partial run
(`/tmp/dr-halted-v2-recovery-read.log`) passed 6 ok / 2 changed / 0 failed:
current-generation source Secondary / target Primary, restored VM Halted,
64 MiB disk size and exact marker read at 1 MiB by a restricted read-only pod.
The reader was removed after success. **This proves recovery can read replicated
data and restore the halted VM object, not complete source cleanup or a running
VM failover.** Source finalizers remain untouched; `Protected=False` and cleanup
remain unresolved rather than being hidden behind the partial-run recap.

Sources:
- [ODF 4.22 Regional DR guide, section 4.11](https://docs.redhat.com/en/documentation/red_hat_openshift_data_foundation/4.22/html/configuring_openshift_data_foundation_disaster_recovery_for_openshift_workloads/index)
- [Ramen namespace SCC retention implementation](https://github.com/RamenDR/ramen/blob/main/internal/controller/drplacementcontrol.go)
- The deployed `oc explain drpc.spec.retainNamespaceSCCAcrossPeers` contract is
  authoritative for this installed release; upstream main alone is not version proof.
