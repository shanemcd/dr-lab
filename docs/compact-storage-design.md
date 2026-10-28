# Compact storage design (live validation in progress)

## Initial runtime findings (2026-10-28)

- Ten vCPUs per compact node was insufficient: default RGW and NooBaa core
  pods remained Pending with `3 Insufficient cpu`. Inventory now allocates
  20 vCPUs per compact node (132 steady-state lab vCPUs; 140 with bootstraps,
  within the host's 160 cores). Default operator resource requests are retained.
- Applied the sizing change to the existing six guests by graceful shutdown,
  persistent libvirt vCPU change, and restart, one node at a time. Each node
  returned Ready with capacity 20 and all three etcd pods Ready before the
  next shutdown. One shutdown exceeded the initial 120-second bound; it was
  allowed to finish normally, not force-powered off. Fresh deployments get
  the corrected sizing directly and require no resize pass.
- Primary LSO created three distinct 120 GiB block PVs; ODF created three OSDs,
  three mons, CSI and NooBaa. NooBaa reached Ready; StorageCluster remains
  Progressing and Ceph HEALTH_WARN. Storage role timed out during the resize
  sequence; this is NOT a completed storage validation. Recovery storage has
  not yet been installed because the role processes sites sequentially.
- Remaining health findings: `MON_CLOCK_SKEW`, `AUTH_INSECURE_CLIENT_KEY_TYPE`,
  `AUTH_INSECURE_KEYS_ALLOWED`, `AUTH_INSECURE_KEYS_CREATABLE`. Guest chrony
  reports Stratum 0 / Not synchronised and unreachable public pool sources.
  Fix reachable time service declaratively and investigate documented Ceph
  key migration requirements; do not silence warnings or weaken health gates.

## Intended configuration

Each managed cluster has three schedulable control-plane nodes. Every node
gets its own dedicated raw 120 GiB virtio disk as `/dev/vdb` at guest creation.
The root disk `/dev/vda` must never be consumed by LSO.

The storage role now uses:

1. OLM subscriptions for Local Storage Operator and ODF 4.22.
2. ODF storage-node labels on all three masters.
3. A `LocalVolume` selecting exactly those hosts and `/dev/vdb`, Block mode,
   storage class `localblock`.
4. Exactly three usable local PVs with node affinity covering all three hosts.
5. A standard internal `StorageCluster` device set: count 1, replica 3,
   portable false, 119 GiB requested per device, mon host path `/var/lib/rook`.
6. StorageCluster Ready, Ceph HEALTH_OK, and a dynamically provisioned 1 GiB
   block RBD PVC binding in a test namespace.
7. NooBaa Ready, a dynamically provisioned ObjectBucketClaim Bound, and
   nonempty issued endpoint/configuration and credential fields. The lab-only
   smoke bucket is reused on reruns and removed with full cluster teardown.
   Credential reads are `no_log`; no live keys are written to repository files.

The object gate tests provisioning, not authenticated S3 put/get or remote
TLS/overlay reachability. Those checks remain necessary in the DR layer.
NooBaa readiness is a prerequisite in the ODF 4.22 Regional DR guide, section
4.5 (and the policy workflow in section 4.8):
https://docs.redhat.com/en/documentation/red_hat_openshift_data_foundation/4.22/html/configuring_openshift_data_foundation_disaster_recovery_for_openshift_workloads/index

There is no SINGLE_NODE override, CSV editing, topology-map/status patch,
replica-1 pool, or post-install VM disk hotplug. The old SNO-specific disk
hotplug/restart tasks have been removed.

Sources consulted:

- ODF 4.22 infrastructure requirements, including three-master compact
  deployments and ODF-only aggregate CPU/memory requirements:
  https://docs.redhat.com/en/documentation/red_hat_openshift_data_foundation/4.22/html/planning_your_deployment/infrastructure-requirements_rhodf
- Historical declarative localblock StorageCluster example (count/replica/
  portable semantics; this is not proof of current end-to-end support):
  https://docs.redhat.com/en/documentation/red_hat_openshift_container_storage/4.3/html/deploying_openshift_container_storage/deploying-openshift-container-storage

The compact guide describes bare-metal clusters; this lab uses virtualized
nodes on one host and is not resilient to failure of that host. Vendor support
for this exact ARM64 virtualized DR combination is not established by these
references. Live provisioning, Ceph health, PVC binding, and DR validation
remain required; lint alone is not sufficient.
