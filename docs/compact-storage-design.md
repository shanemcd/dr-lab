# Compact storage design (not yet live-validated)

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
