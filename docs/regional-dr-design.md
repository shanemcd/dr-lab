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

## Live transport and policy implementation (2026-10-28)

Stage10 now also runs a real application probe, not only add-on conditions.
Unprivileged Python HTTP servers run on each site's **second master**, not the
first-master gateways, with hostNetwork false and no service-account token.
From each endpoint pod, urllib (explicitly bypassing HTTP proxies) fetches both
the other site's PodIP and ClusterIP and asserts the remote site identity.
Both directions passed. Standalone rerun: `playbooks/probe_overlay.yml` inside
the collection. The ARM64 Python image is digest-pinned after runtime validation.
A rollout exposed old terminating pods in the selector; probe selection now
excludes them rather than weakening endpoint uniqueness. Four successful HTTP
exchanges establish application traffic over the overlay, not just a tunnel.
An additional probe now uses those same restricted pods to perform authenticated
S3 PUT/GET/content-compare/DELETE against the other site's actual S3 route.
It uses the issued lab-only OBC credentials, AWS SigV4, an explicitly trusted
remote ingress signer, hostname verification, no HTTP proxy and no insecure TLS
option. Credentials reach the pod through `oc exec` stdin, with Ansible no_log;
no credential is placed in the oc/Python process arguments, source control or
persistent probe files. Ansible's normal root-owned module transport may use
temporary files according to connection settings; this is not a zero-disk or
memory-only secret-transport claim.
Both directions passed live. S3 route traffic proves authenticated remote object
I/O with verified TLS (via ingress), **not** S3 over the PodIP overlay.
The separate PodIP/ClusterIP HTTP probe proves that overlay. Neither alone
establishes replicated VM data or completed failover.

For stage12 we inspected the **deployed** odf-multicluster-console source map,
`exposed-createDataPolicy-chunk.js.map`, module
`packages/mco/components/create-dr-policy/utils/k8s-utils.ts`, from image
`registry.redhat.io/odf4/odf-multicluster-console-rhel9@sha256:4685579864d3b0cd0c727c97fae7bc1838920dce59a0d65986e46253ee9f9873`.
Its DataFoundation branch creates a MirrorPeer with manageS3 true, type async,
and two storageClusterRef entries, then creates DRPolicy with drClusters,
schedulingInterval and replicationClassSelector (empty unless clone flattening
is requested). It does **not** manually create DRClusters or copy S3 credentials;
those are owned by orchestration. Stage12 reproduces that payload, refuses
changes to existing identity/spec fields, and waits for typed Validated conditions,
DR-cluster operator rollout and StorageClusterPeer Peered on both sites.
This is implementation evidence, not a claim that policy/mirroring/failover
already passed; actual policy validation remains in progress.

At first policy creation, tokenexchange/onboarding/S3-secret creation produced
normal retries, plus a recovered orchestrator panic while endpoint lists were
still empty. Both StorageClusterPeers subsequently reached Peered; namespace
mirroring daemon/image/group/overall health all became OK. Only the primary
DRCluster existed at the last snapshot. The release-4.22
[MirrorPeer controller](https://github.com/red-hat-storage/odf-multicluster-orchestrator/blob/release-4.22/controllers/odf/mirrorpeer_controller.go)
requeues missing S3 secrets using rate-limited `Requeue: true`; its watches cover
generation changes, tokenexchange add-ons and selected ConfigMaps, not Secrets.
Repeated early retries can therefore delay observation after a secret arrives.
We are allowing normal reconciliation, not forcing a restart or status patch.
This delay is a diagnosis hypothesis until the next reconciliation is observed.

## Discovered workload protection contract (not yet deployed)

The same deployed console's
`packages/mco/components/discovered-application-wizard/utils/k8s-utils.ts`
creates a dummy `cluster.open-cluster-management.io/v1beta1` Placement in
`openshift-dr-ops` with the protected-application annotation and
`spec.predicates: []`. It creates a DRPlacementControl alongside it, with
preferredCluster, protectedNamespaces, pvcSelector, kubeObjectProtection
(captureInterval plus either recipeRef/recipeParameters or kubeObjectSelector),
drPolicyRef and a fully typed placementRef. This avoids inventing a GitOps
application solely to manage a discovered VM. A recipe is not automatically
inserted by this wizard. The live DRPC CRD confirms those fields.

The VM stage must still determine an appropriate VM-consistent protection
recipe (if required), establish actual replication/capture readiness and
perform failover, not only create these objects. Any infrastructure-powered
source fencing must be ownership-guarded and observed complete before target
activation; a manually asserted fence without physical evidence is prohibited.
Source and recovery VMs must not run simultaneously. No VM, DRPC or actual
failover has been validated yet, and nested KVM is still unavailable.

## Live catalog discovery (2026-10-27)

Read-only discovery against the rebuilt dr-recovery API returned 635 package manifests.
The following entries are published by `redhat-operators`:

| Package | Configured channel exists | Current CSV in that channel |
| --- | --- | --- |
| advanced-cluster-management | release-2.17 | not captured |
| local-storage-operator | stable | not captured |
| odf-operator | stable-4.22 | odf-operator.v4.22.6-rhodf |
| openshift-gitops-operator | latest | not captured |
| odf-multicluster-orchestrator | stable-4.22 | odf-multicluster-orchestrator.v4.22.6-rhodf |
| redhat-oadp-operator | stable | oadp-operator.v1.6.1 |
| kubevirt-hyperconverged | stable | kubevirt-hyperconverged-operator.v4.22.12 |

OADP's advertised version meets the guide's >=1.4 requirement. Its CSV description
advertises OwnNamespace only; orchestrator advertises AllNamespaces only. ODF and
virtualization advertise OwnNamespace and SingleNamespace. These match the intended
OperatorGroup scopes. Catalog publication does NOT establish ARM64 operand image
availability, successful OLM resolution, runtime compatibility or vendor support.
No subscriptions were created during this discovery. Channel heads can change;
the runtime catalog/CSV checks remain necessary on every deployment.

## Policy automation contract (4.22 guide section 4.8)

The documented console flow creates a DRPolicy **and** two DRClusters. Applying
only a hand-written DRPolicy is not equivalent to that flow. Inspect the current
orchestrator APIs and console implementation before reproducing it in Ansible;
do not assume the old lab's MirrorPeer manifest is still the entry point.

- Unique policy name per interval; minimum interval one minute. The guide says
  SchedulingInterval, ReplicationClassSelector, VolumeSnapshotClassSelector and
  DRClusters cannot be edited. Refuse incompatible existing policy specs rather
  than silently attempting to patch these fields.
- Region and S3ProfileName on DRClusters are also non-editable. Capture desired
  identities before creation and validate them on reruns.
- Require successful policy validation and **both** DRCluster validations, including
  object-bucket access from the hub to each site. Check condition types instead
  of relying on the guide's example positional `.status.conditions[2]` query.
- Require `odr-cluster-operator` CSV Succeeded and `ramen-dr-cluster-operator`
  rollout in `openshift-dr-system` on both sites; the hub operator alone is not
  sufficient.
- Require each site's `StorageClusterPeer/<remote-managedcluster-name>-peer`
  state `Peered`, followed by healthy mirroring. DRPolicy validation alone is not
  a complete replication check. The initial policy also installs VolSync for
  CephFS; do not introduce a conflicting manual subscription.

These are requirements extracted from the guide, not claims of live completion.

## Remaining implementation gates

- Establish actual operator resolution and runtime compatibility on ARM64; the catalog names/channels above are discovered, not installed.
- Managed Submariner automation is implemented in stage10: cluster-set broker without Globalnet, explicit first-master gateway, SubmarinerConfig and ManagedClusterAddOn per site, then gateway/agent/connection conditions. Runtime CRD/behavior and an end-to-end cross-overlay probe remain unverified. The default NAT/cable-driver behavior is retained rather than guessing unverified CRD fields.
- API procedure source: https://docs.redhat.com/en/documentation/red_hat_advanced_cluster_management_for_kubernetes/2.17/pdf/networking/uninstalling-submariner-manually (Networking section1.4.21). Live deployment required the documented deprecated installNamespace: submariner-operator; omitting it sent OLM to the generic add-on namespace. Source now sets it and the add-on framework migrates it to status.namespace. Default gateway selection is overridden by labeling the designated compact master before enabling the add-on.
- Stage11_dr_prerequisites implements GitOps subscriptions on all three clusters, followed by the hub orchestrator subscription. It validates configured channels against the live redhat-operators catalog, waits for each subscription's specific installed CSV (not arbitrary namespace CSVs), then requires the hub DR CRDs and ramen-hub-operator rollout. GitOps latest and orchestrator stable-4.22 exist in the rebuilt site's live catalog; installation and runtime compatibility have NOT been established.
- Stage11 also implements section4.7 cross-cluster ingress CA trust before installing operators. It preserves existing custom proxy CA certificates, checks ownership of its ConfigMap, de-duplicates PEM blocks, and changes only proxy.spec.trustedCA. Offline tests exercise actual Ansible union/rendering twice, including custom trust preservation. Live trust propagation and S3 TLS connectivity are still unverified; applying trust may trigger Machine Config Operator reconciliation.
- Stage11 now installs OADP on both sites BEFORE orchestrator/DR configuration, following section4.16.1 (OADP >=1.4 required). Late OADP installation otherwise requires restarting DR-cluster operators for CRD discovery. Subscription and CSV waits support a selected namespace; GitOps/orchestrator keep openshift-operators, OADP uses openshift-adp with a namespace-scoped OperatorGroup. Existing conflicting groups are refused. The stable channel exists in the rebuilt site's live catalog and advertises OADP 1.6.1; successful installation and ARM64 operand compatibility remain to be verified.
- OADP DPA follows section4.16.1 exactly: backupImages false, nodeAgent disabled, Velero openshift/aws/kubevirt plugins and noDefaultBackupLocation true, then waits for Velero rollout. This does NOT prove backup/restore: orchestrator-created DR secrets, S3 access, BackupStorageLocations and actual object recovery remain unverified. No hand-authored S3 credentials or redundant disk backup paths are configured.
- Implement documented peering and policy configuration against live CRDs rather than guessing fields. Orchestrator subscription alone does not configure or validate DR.
- Verify mirroring/S3 metadata/OADP, then protect a minimal ARM64 VM.
- Only after cluster/storage/DR layers run, investigate software-emulated virtualization on Neoverse-N1 (no nested KVM). Never report a successful failover without observing a target-side running VMI and protected state.
