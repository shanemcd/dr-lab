# Recovery compatibility and manual-assistance boundary

## Observed combination

The [2026-10-28 x86_64 validation](current-validation.md) used OpenShift
4.22.16, ODR 4.22.6-rhodf, OADP 1.6.2 and Velero
`v1.18.2-rc.2-OADP`. The observed Ramen image was
`registry.redhat.io/odf4/odr-rhel9-operator@sha256:22f55c1162dfea43a8ff0e6fc5393d435b2d7eeacc2655da1cf4cb3bcaaa3cfd`.
These are observations, **not a vendor-certified compatibility matrix**.

Catalog channels in inventory select rolling operator releases. A channel being
available and its CSV succeeding does not establish recovery interoperability.
Record CSV versions, deployment image digests and OADP/Velero versions on each
site before recovery. Recheck vendor support guidance for the releases actually
installed; do not assume a future channel resolves this problem. Changing a
channel is not a safe downgrade procedure. No supported automatic fix or
validated alternate version combination was established during this exercise.

## Failure mechanism

Every tested relocation/failover initially stalled at kube-object recovery:

1. Destination Ramen created placeholder Velero Backup CRs for captured objects.
2. Velero marked these placeholders Failed with
   `backup execution failed: backup already exists in object storage`.
3. Ramen requested Restore from a Failed placeholder. Velero rejected it with
   `is in phase "Failed" and cannot be used as a restore source`.
4. A replicated PVC could be Bound and DRPC Relocated/Completed or FailedOver
   while **no VM/VMI existed**. Those controller phases were not usable recovery.

Authenticated, verified-TLS object-store inspection found the original metadata
Completed and archives containing namespace, VM and VMI definitions. Native
metadata sync subsequently restored them successfully; manual reconstruction of
the VM was not needed.

Public reference source matches this mechanism, but was not proven identical
to the installed downstream build:

- [Ramen restore request implementation](https://github.com/ramendr/ramen/blob/main/internal/controller/kubeobjects/velero/requests.go)
- [Velero restore controller](https://github.com/openshift/velero/blob/oadp-dev/pkg/controller/restore_controller.go)

Do not patch backup status to Completed, enable global backup sync, delete S3
captures or weaken TLS/admission/security to work around it. Ramen deliberately
controls capture visibility; indiscriminate syncing can resurrect stale objects.

## Assisted recovery procedure used in this lab

This is an **expert-operated lab diagnostic**, not a supported general recovery
playbook. It assumes the separate [single-writer/fencing safeguards](operations.md#recovery-safety)
are already established. Do not apply it to an active source or an unrelated
application. Preserve private evidence and obtain product support guidance for
production use. There is intentionally no copy-and-paste destructive command.

1. Inspect the exact DRPC generation/action/destination, VRG state and source
   isolation/cleanup. Verify neither site currently has a writable guest or
   PVC-consuming pod. Record affected object UIDs/resourceVersions and controller
   replica counts. Preserve all backup captures and credentials privately.
2. On the destination only, pause the specific Ramen cluster operator with a
   resourceVersion-guarded scale from one to zero; wait for its pods to stop.
   This interrupts reconciliation for other applications on that cluster too:
   use only an isolated lab or obtain explicit wider coordination.
3. Inspect **fully qualified** `backups.velero.io`, `restores.velero.io` and
   `backupstoragelocations.velero.io` in `openshift-adp`. Select only terminal
   Failed placeholder Backups and FailedValidation Restores owned by this DRPC.
   Delete those CRs with UID preconditions and normal finalizer handling. Refuse
   Backup deletion if finalizers exist. Never delete the original S3 data or a
   successful backup as part of this procedure.
4. Identify the actual current capture number, source profile, bucket and prefix
   from the failed restore and existing BSL. Do not infer them from a previous
   recovery or reuse an old capture. Clone that BSL spec into a separately named
   temporary BSL, retaining credentials and CA, with `accessMode: ReadOnly` and
   `backupSyncPeriod: 5s`. Never print credential values. Keep all other locations
   unchanged. A five-second period does not guarantee immediate native sync.
5. Wait for Velero to import the **expected original** backup as Completed;
   inspect its name, capture, timestamps and location. If it does not import,
   diagnose rather than forging status or broadening deletion. Resume the
   destination Ramen operator to its recorded replica count. If any step fails
   after pausing, inspect the partial state and explicitly restore reconciliation
   once safe; never leave an unnoticed paused controller.
6. Wait for VM/VMI Running, Ready and AgentConnected. Read the existing durable
   marker via strict original SSH host identity and compare the independently
   retained hash. Do not reprovision or recreate markers. Check source absence,
   current-generation protection and both checkpoint timestamps separately.
7. Remove only the temporary BSL with its UID precondition and normal finalizer
   handling. Verify Ramen available, no temporary debug configuration left, and
   the intended single writer. Keep failed/assisted timing in the evidence.

This procedure succeeded repeatedly in the isolated lab, including recovery of
both original and separate post-recovery markers. It is not automated in `site`
or fixture playbooks. Request-to-guest timings include manual intervention;
none is an unattended RTO guarantee. ARM guest recovery remains unvalidated.
