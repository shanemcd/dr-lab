# Configuration contract

Use `inventory/group_vars/all/` as the source of defaults and an ignored
`local.yml` for overrides; pass the same overrides to every entrypoint, including
teardown. These are deployment inputs, not a supported in-place migration API.
Read [getting started](getting-started.md) before provisioning.

## Settings that must agree

| Area | Inputs and constraints |
| --- | --- |
| Native platform | `lab_arch` must equal the discovered managed-host architecture; `ocp_arch` must match. Profiles provide native machine, console, emulator and packages. Cross-architecture execution is rejected. |
| Release artifacts | Changing `ocp_version` requires installer/client/ISO pins for that release and native architecture in `release_pins`. The ISO name and checksum must match the installer's stream metadata. A version string alone is not an upgrade procedure. |
| Cluster selection | `clusters` defines the topology. `acm_cluster` selects its hub; ordered `acm_spokes` selects initial source then recovery. `storage_clusters`, `virtualization_clusters` and protection/overlay selectors must refer to the same two sites. Renaming only a topology entry is insufficient. |
| Host resources | `compact_master_*`, `hub_*` and `bootstrap_*` determine capacity checks. CPU overcommit requires explicit policy; keep memory/disk headroom. Bootstrap resources count during installation. |
| Storage | `compact_master_data_disk` must accommodate `storage_device_request` with headroom. `storage_local_devices` identifies dedicated guest data disks, not host root devices. Do not resize populated OSDs through inventory edits. |
| Workload | Optional `workload.yml` selects namespace, name, immutable native image, PVC size and storage class. `workload_storage_class` must exist on both sites; it defaults to `storage_rbd_storageclass`. Initial provisioning/protection refuses existing state and is not a recovery command. |
| Identity and paths | `lab_user` resolves a real managed-host account. Defaults derive paths from its home, not a particular username. Review teardown restrictions before choosing custom paths; arbitrary paths or shell metacharacters are not universally supported. |

## Network design boundaries

The network model is **IPv4 /24**, not an arbitrary-CIDR network builder.
Change `lab_subnet_prefix` (three decimal octets) as a unit; keep
`lab_subnet_netmask=255.255.255.0` and the derived `/24` CIDR. Bridge addressing,
DHCP and node derivations assume that shape. The default prefix is an example,
not a requirement for the author's LAN.

Choose distinct gateway, node, bootstrap, VIP and probe suffixes within the
usable host range (1–254), outside the DHCP free range. Existing checks detect
some collisions but are not a complete configuration validator. Independently
review all addresses and routes, including VPNs. Per-cluster pod and service
CIDRs must be nonoverlapping across sites and with the host/lab networks;
Submariner Globalnet is intentionally not enabled.

`base_domain` controls generated cluster DNS names; `mac_base` plus suffixes
controls guest MACs. Keep them stable for a deployed lab. `upstream_dns_servers`
can override host resolver discovery. The gateway relays synchronized NTP to
guests; check its real upstream synchronization rather than substituting an
unsynchronized local clock. Do not alter the management interface to fix lab
DNS. See [operations](operations.md) for access and bounded diagnostics.

## Credentials and dependencies

`secrets.yml` contains paths only. Keep pull-secret values, generated SSH keys,
installer credentials and object-store keys out of Git; extra-vars files with
secrets need private permissions as well as ignore rules. Ignoring a file does
not untrack a previously committed secret. See [compatibility](compatibility.md)
for the exact observed operator versions and manually assisted restore limit:
rolling channels do not lock a reproducible operator matrix.

Only local-host provisioning has been exercised. Package repositories,
firmware availability, nested virtualization and architecture-specific operator
support remain host/platform prerequisites, not properties guaranteed by YAML
rendering. ARM execution remains unvalidated; see [platforms](platforms.md).
