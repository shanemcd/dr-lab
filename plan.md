# dr-lab rebuild: real compact clusters, one-shot bring-up, no hacks

Mission (user, 2025-10-28): bring up the ENTIRE lab in one shot with no hacks;
grow SNOs into real clusters where needed; teardown + one-shot redeploy must
work; once DR is deployed, create a test VM and perform a failover.

## Why rebuild

Internal (compact single-node) ODF on ODF 4.22 requires an ocs-operator env hack
(`SINGLE_NODE=true`) and hits an upstream-fixed bug in release-4.22
(`GetKeyValues("osd")` returns "" -> invalid OSD topologySpreadConstraints; fixed
in release-4.23+). Rather than patch operator images, we move to the fully
supported topology.

## Target architecture

- **dr-hub**: stays SNO (BiP). Runs ACM only; no ODF. No VIPs (unchanged).
- **dr-primary, dr-recovery**: **3-master compact clusters** (compute replicas 0,
  masters schedulable). Real UPI flow:
  - bootstrap VM (temporary) + 3 master VMs per cluster
  - haproxy on the lab host, per-cluster API VIP on the lab bridge:
    6443 + 22623 -> bootstrap during install, -> masters after; 80/443 -> masters
  - masters boot RHCOS ISO with per-node ignition baked via fw_cfg
    (master.ign merged with per-node NM keyfile/hostname — same merge machinery
    as the BiP path; no MCS dependency at boot)
  - wait-for bootstrap-complete, destroy bootstrap, reconfigure LB, converge,
    approve CSRs
- **Storage (real ODF)**: each compact node gets a second virtio disk (data).
  LSO discovery + LocalVolume (`localblock`) on /dev/vdb, ODF subscription,
  StorageCluster internal mode with device sets on localblock, failureDomain
  host. No env hacks, no operator patches.
- **DR**: RamenDR Regional-DR — ODR hub operator on dr-hub, ramen-dr-cluster
  operator + ODF on both managed clusters, mirror peer, DRPolicy,
  VolumeReplicationClass (RBD mirroring), VolumeSnapshotClass, DRPlacementControl
  apps.
- **Test**: OpenShift Virtualization VM on dr-primary protected by DR, failover
  to dr-recovery.

## Resource budget (host: 160 cores, 501 GiB, ~1.8 TB free)

| VM | count | vCPU | RAM | disks |
|----|-------|------|-----|-------|
| dr-hub (SNO) | 1 | 12 | 40G | 200G |
| master (compact) | 6 | 10 | 40G | 120G root + 120G data |
| bootstrap (transient, 1 per install) | 1 | 4 | 16G | 60G |

Steady: ~72 vCPU, ~280G RAM, ~1.7 TB. Fits.

## IP plan (single /24, 192.168.126.0/24 — unchanged network role)

- .11  dr-hub (SNO, BiP — no VIP)
- .12  dr-primary API/ingress VIP (on bridge, haproxy)
- .13-.15 dr-primary masters
- .16  dr-recovery API/ingress VIP
- .17-.19 dr-recovery masters
- .21/.22 bootstrap nodes (transient, DHCP reservations)

## Work phases

1. topology.yml redesign (clusters w/ node lists, VIPs, bootstrap specs)
2. network: VIP bridge addresses, DNS api/api-int/apps -> VIP per compact cluster
3. loadbalancer role: haproxy (systemd container or host package) per cluster,
   bootstrap/masters mode switch
4. install_config: multi-node path (manifests, bootstrap.ign, per-master
   ignition merge), keep BiP path for hub
5. vms: data disks on masters, bootstrap VM lifecycle
6. cluster_install: bootstrap-complete, LB switch, CSR approval, convergence
7. storage layer rewrite (LSO + real ODF)
8. acm layer adapt (unchanged hub)
9. virtualization layer (exists — 07) re-verify
10. dr layer: RamenDR per upstream docs
11. test VM + failover runbook/verification
12. full teardown + one-shot redeploy verification, docs, commit
