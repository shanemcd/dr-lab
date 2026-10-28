# Compact cluster storage design

## Configuration contract

Each managed cluster has three schedulable control-plane nodes. Each node gets
one dedicated raw virtio data disk (`/dev/vdb`) at guest creation. The root disk
(`/dev/vda`) must never be selected for local storage. Default data disks are
120 GiB; overrides for a new test deployment must also adjust
`storage_device_request` to fit. See [getting started](getting-started.md).

The storage role provisions:

1. Local Storage Operator and ODF 4.22 through normal OLM subscriptions.
2. ODF storage-node labels on all three masters.
3. A Block-mode `LocalVolume`, class `localblock`, selecting exactly the expected
   hosts and `/dev/vdb`.
4. Exactly three usable local PVs with node affinity covering all three hosts.
5. An internal `StorageCluster` device set: count 1, replica 3, portable false,
   default 119 GiB request per device and mon host path `/var/lib/rook`.
6. StorageCluster Ready, Ceph HEALTH_OK and a dynamically provisioned 1 GiB
   block RBD smoke PVC bound.
7. NooBaa Ready, a dynamic ObjectBucketClaim Bound, and nonempty issued endpoint,
   configuration and credential fields. Credential reads use `no_log`.

The object smoke gate proves provisioning, not authenticated S3 exchange,
replication or recovery. Separate cross-site transport, TLS, object capture,
and disk checkpoint checks remain necessary. The lab smoke resources are reused
on reruns and disappear with cluster teardown.

No SINGLE_NODE override, CSV editing, topology/status patch, replica-1 pool or
post-install VM disk hotplug is used. Three replicas within virtual nodes on a
single physical host do **not** protect against that host's failure.

## Sizing

Defaults allocate 20 vCPU and 40 GiB RAM to each compact node. In the historical
ARM experiment, ten vCPUs left default RGW/NooBaa pods Pending with
`3 Insufficient cpu`. Raising guest CPUs to 20 resolved scheduling pressure
without reducing vendor resource requests. Host CPU overcommit is a separate,
explicit policy; it does not reduce Kubernetes allocatable CPUs.

The historical live resize was performed one node at a time with graceful
shutdown, persistent vCPU change and readiness/etcd checks before the next node.
Fresh deployments use the corrected sizing directly; changing a variable on a
live deployment is not an automated rolling resize procedure.

## Time synchronization

Ceph requires synchronized clocks. Historical guests could not reach public NTP
pools and reported `MON_CLOCK_SKEW`, Stratum 0 and Not synchronised. Host
preparation now enables an owned chrony relay rule restricted to the lab subnet.
It does not use `local stratum` or advertise an unsynchronized clock. Ignition
configures the master MachineConfig to use the lab gateway.

For existing clusters, `shanemcd.dr_lab.sync_time` reconciles this configuration
and waits for master pools. Normal MCO drains may reboot nodes; a SNO hub's API
will be unavailable during reboot. Teardown removes only the owned relay rule,
preserving host upstreams. Investigate actual clock status instead of muting
Ceph clock warnings.

## CephX security caveat from the historical ARM deployment

A HEALTH_OK gate is not evidence of AES256K-only client security. Direct Ceph
inspection found vendor-installed sticky mutes for
`AUTH_INSECURE_CLIENT_KEY_TYPE`, `AUTH_INSECURE_KEYS_ALLOWED` and
`AUTH_INSECURE_KEYS_CREATABLE`. The lab did not add mutes or weaken health
checks. Reinspect actual vendor defaults on each release.

Historical daemon/admin keys already used AES256K. Six AES client identities
remained: four CSI identities, `client.ocs-metrics-exporter-ceph-auth`, and
`client.rbd-mirror-peer`. Do not rotate keys or restrict ciphers solely to clear
a health warning: storage access can break. Upstream AES256K CSI keys require
compatible kernel support and Ceph-CSI >=3.16.3. The historical RHCOS
`5.14.0-687.50.1.el9_8.aarch64` libceph module contained
`ceph_krb5_encrypt`/`ceph_krb5_decrypt`; version numbers alone do not rule out
backports. Verify vendor compatibility and actual mounts before rotation.
Use the owning StorageCluster managed-resource CephX API, not generated Secrets
or operator Deployments, for any supported change.

## Evidence and references

The historical ARM rebuild passed storage provisioning and health gates; see
[rebuild evidence](rebuild-validation.md). That does not certify the current
x86_64 deployment; its status is in [current evidence](current-validation.md).
Neither result establishes running-VM failover or production support.

- [ODF 4.22 infrastructure requirements](https://docs.redhat.com/en/documentation/red_hat_openshift_data_foundation/4.22/html/planning_your_deployment/infrastructure-requirements_rhodf)
- [ODF 4.22 Regional DR guide](https://docs.redhat.com/en/documentation/red_hat_openshift_data_foundation/4.22/html/configuring_openshift_data_foundation_disaster_recovery_for_openshift_workloads/index)
- [Rook CephX key rotation](https://www.rook.io/docs/rook/v1.19/Storage-Configuration/Advanced/cephx-key-rotation)
- [Ceph compatibility advisory](https://ceph.io/en/news/blog/2026/v20-2-4-v19-2-6-combo-released)
