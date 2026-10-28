# Regional-DR implementation notes (not yet deployed)

## Authoritative workflow

ODF 4.22 Regional-DR guide:
https://docs.redhat.com/en/documentation/red_hat_openshift_data_foundation/4.22/html/configuring_openshift_data_foundation_disaster_recovery_for_openshift_workloads/rdr-solution

Sections 4.4–4.8 require:

1. Three network-reachable clusters; RHACM hub and two healthy ODF sites.
2. Non-overlapping pod/service CIDRs, with RHACM Submariner connecting private networks. Same libvirt L2 alone does NOT connect the OVN overlays. Our inventory uses distinct CIDRs, so no Globalnet is planned. Do not enable irreversible StorageCluster network.multiClusterService just to make connectivity work; the guide requires that only when Globalnet is enabled.
3. Ready StorageCluster AND Ready NooBaa on both sites. Do not disable the object store: MCG is part of the documented metadata protection path.
4. OpenShift GitOps before ODF Multicluster Orchestrator on the hub. Install orchestrator in openshift-operators, all namespaces. Its dependency installs OpenShift DR Hub; do not manually create conflicting hub-operator subscriptions.
5. Configure SSL trust across sites for metadata S3 access (section 4.7).
6. DRPolicy with unique name/interval and corresponding DRClusters; require Validated conditions and successful mirroring before a workload test.
7. Discovered-application protection requires OADP on both sites. The VM recipe protects Kubernetes objects with OADP and disk state with CSI replication; these are separate checks.

The documented supported Regional-DR environments are VMware, bare metal and hybrid cloud. This virtualized ARM64 single-physical-host lab is NOT evidence of a supported production HA design.

## ACM implementation change

The earlier role installed standalone MCE, which provides registration but not the complete ACM services required here. The role now installs advanced-cluster-management/release-2.17 in open-cluster-management and creates MultiClusterHub with availabilityConfig: Basic for the SNO hub. MCH owns its bundled MCE; do not separately install standalone MCE. Search collector is now enabled for both spokes. Runtime confirmation remains pending the new core installation.

SNO Basic availability reference (older installation guide; live 2.17 CR schema/catalog must still be checked):
https://docs.redhat.com/en/documentation/red_hat_advanced_cluster_management_for_kubernetes/2.8/html/install/installing

## Prior lab reference (not a deployment template)

/root/ocp-lab/docs/odf-ramendr-acm-discovered-vm-setup.md records a working x86 lab with MirrorPeer, DRPolicy, Submariner, OADP and vm-recipe. Its SINGLE_NODE storage tweaks are deliberately NOT carried over. /root/ocp-lab/manifests/acm-vm-dr contains workload/DRPC examples to adapt after infrastructure validation. Never commit the old lab's credentials or copy its kubeconfigs.

## Remaining implementation gates

- Discover exact 4.22 operator package/channel/CSV compatibility from the rebuilt clusters.
- Managed Submariner automation is implemented in stage10: cluster-set broker without Globalnet, explicit first-master gateway, SubmarinerConfig and ManagedClusterAddOn per site, then gateway/agent/connection conditions. Runtime CRD/behavior and an end-to-end cross-overlay probe remain unverified. The default NAT/cable-driver behavior is retained rather than guessing unverified CRD fields.
- API procedure source: https://docs.redhat.com/en/documentation/red_hat_advanced_cluster_management_for_kubernetes/2.17/pdf/networking/uninstalling-submariner-manually (Networking section1.4.21). Deprecated installNamespace is deliberately omitted. Default gateway selection is overridden by labeling the designated compact master before enabling the add-on.
- Install GitOps and orchestrator; implement documented peering, trust and policy configuration against live CRDs rather than guessing fields.
- Verify mirroring/S3 metadata/OADP, then protect a minimal ARM64 VM.
- Only after cluster/storage/DR layers run, investigate software-emulated virtualization on Neoverse-N1 (no nested KVM). Never report a successful failover without observing a target-side running VMI and protected state.
