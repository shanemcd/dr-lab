# Project scope and acceptance

The maintained operator entrypoint is [getting started](docs/getting-started.md).
The current [topology and status](README.md), [platform matrix](docs/platforms.md),
and [validation criteria](docs/validation.md) supersede host-specific planning
notes. Historical deployment reports are evidence for their stated scope only.

## Scope

- Reproducible deployment on native x86_64 and aarch64 Red Hat-family hosts.
- Clear capacity, nested virtualization, network and credential prerequisites.
- ACM hub plus two compact workload clusters with internal replicated ODF.
- Submariner, OADP and Ramen-based protection of a real PVC-backed running VM.
- Public documentation without credentials or assumptions about an author's host.

## Acceptance gates

1. Offline tests and playbook syntax checks pass on the supported controller.
2. Host preflight and the complete infrastructure deployment pass.
3. A stock guest runs on each managed cluster with hardware virtualization.
4. VM disk and object checkpoints are protected and recoverable.
5. Planned relocation preserves guest data and single-writer safety.
6. Fenced unplanned failover recovers a running guest with measured RPO/RTO.
7. Replication resumes and failback passes the same data-integrity checks.

Native x86_64 infrastructure, running guests at both sites, checkpoints, planned
relocation, physically isolated failover and assisted return have been observed.
Both the original marker and a separate post-recovery marker survived return to
the initial primary. This is **assisted recovery evidence**, not unattended
reproducibility: each restore needed native Velero metadata import. Recorded
timings include that assistance; maximum ongoing-write RPO remains unmeasured.
See [current evidence](docs/current-validation.md) and
[compatibility](docs/compatibility.md) for the exact scope and remaining limits.

The historical ARM host passed infrastructure gates but could not execute the
required nested guest; current ARM execution remains unvalidated. Halted-VM
relocation is not acceptance of running-VM recovery. See
[hardware limitations](docs/hardware-blocker.md) for that historical result.

Do not remove readiness or safety checks to turn a blocked gate into a pass.
Do not claim independent physical-site resilience for a single-host topology.
