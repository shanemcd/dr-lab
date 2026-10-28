# Regional DR design

## Architecture and dependencies

The lab implements the [ODF 4.22 Regional DR workflow](https://docs.redhat.com/en/documentation/red_hat_openshift_data_foundation/4.22/html/configuring_openshift_data_foundation_disaster_recovery_for_openshift_workloads/rdr-solution).
The single-host virtualized topology is experimental, not a production support
or availability claim. Native architecture profiles do not certify operands.

Required order:

1. One ACM hub and two healthy compact ODF clusters with Ready NooBaa.
2. Non-overlapping pod/service CIDRs and working cross-site transport.
3. Cross-site TLS trust, GitOps and OADP prerequisites.
4. Hub ODF Multicluster Orchestrator, peering and a validated DR policy.
5. A real running PVC-backed VM with current disk and object checkpoints.
6. Separate planned relocation, fenced unplanned failover and failback tests.

Same libvirt L2 does not connect OVN pod/service overlays. Submariner provides
that transport. No Globalnet is configured because the networks do not overlap;
`StorageCluster.network.multiClusterService` is not enabled simply to repair
connectivity (the guide requires it for Globalnet).

## ACM and transport

The ACM role installs `advanced-cluster-management/release-2.17` in
`open-cluster-management` and creates a Basic-availability MultiClusterHub for
the SNO hub. MCH owns bundled MCE; a standalone MCE subscription would conflict.
Managed sites require search, governance-policy-framework and
config-policy-controller add-ons as well as registration. Historical testing
found missing governance agents prevented Ramen S3 credential distribution even
though hub ACM was healthy. Credentials must flow through normal controllers,
not manual copying.

Stage 10 creates the cluster-set broker, labels each site's first master as its
gateway, and creates SubmarinerConfig/ManagedClusterAddOn resources. The
installed API required the documented deprecated `installNamespace:
submariner-operator`; the framework migrates this to status.namespace. Default
NAT/cable-driver behavior is retained.

Connection conditions are followed by restricted, tokenless HTTP pods on each
site's second master (not the gateway). Each fetches both remote PodIP and
ClusterIP and checks the site identity, without host networking or HTTP proxies.
Four successful exchanges prove application overlay traffic, not just tunnels.
`shanemcd.dr_lab.probe_overlay` reruns this diagnostic.

A separate authenticated S3 probe uses issued lab-only OBC credentials, AWS
SigV4, remote ingress trust and hostname verification to PUT/GET/compare/DELETE.
S3 route traffic proves authenticated remote object I/O with TLS, **not** S3
over the PodIP overlay. Credentials pass through `oc exec` stdin under
`no_log`, not process arguments or committed files. Normal Ansible transport
may still use protected temporary files; this is not a memory-only claim.

## Prerequisites and policy

Stage 11 installs GitOps on all clusters and OADP on both managed sites before
hub orchestration. It checks configured channels in the live catalog and waits
for each subscription's own CSV. GitOps/orchestrator use `openshift-operators`;
OADP uses a namespace-scoped OperatorGroup in `openshift-adp`. Conflicting groups
are refused. OADP needs >=1.4; the historical catalog advertised 1.6.1.
The DPA disables image backup/nodeAgent, enables openshift/aws/kubevirt Velero
plugins and uses `noDefaultBackupLocation: true` per the guide. A ready Velero
deployment is not proof of successful object capture/restore.

Cross-cluster ingress trust preserves custom proxy CA certificates, checks owned
ConfigMaps and de-duplicates PEM blocks. Trust updates may trigger MCO
reconciliation. Proxy trust alone did not fix historical Velero BSL failures:
`tls: failed to verify certificate: x509: certificate signed by unknown authority`.
Stage 12 also merges documented base64 `caCertificates` into hub Ramen S3
profiles, preserving other generated fields and waiting for spoke propagation.
There are no insecure TLS flags, generated BSL patches or operator restarts.

Stage 12 follows the ODF console's DataFoundation payload: an async MirrorPeer
with `manageS3: true` and two storageClusterRef entries, then a DRPolicy with
unique name/interval, drClusters and replicationClassSelector. Orchestration owns
DRClusters and S3 credentials. Do not mix this with hand-created conflicting
operator subscriptions or copy credentials from another lab.

The role refuses incompatible immutable policy/identity changes and requires:

- MirrorPeer Ready and typed DRPolicy/DRCluster Validated conditions.
- Both managed DR-cluster operator rollouts, not only hub readiness.
- Both StorageClusterPeers Peered and healthy namespace mirroring summaries.
- Cross-site S3 trust configured for object protection.

The guide makes scheduling interval (minimum one minute), replication/snapshot
selectors and DRClusters immutable. DRCluster region/S3 profile identity is also
not a routine edit. Do not index conditions positionally or patch status to make
a gate pass. Initial tokenexchange/onboarding may retry; historical reconciliation
completed without forced restarts despite an early recovered orchestrator panic.

## Discovered VM protection contract

A discovered application does not require a dummy GitOps application. The
installed console creates a Placement in `openshift-dr-ops`, with the
protected-application annotation and `spec.predicates: []`, plus a
DRPlacementControl with preferredCluster, protectedNamespaces, pvcSelector,
kubeObjectProtection, drPolicyRef and a fully typed placementRef. The object
protection includes captureInterval and recipeRef/recipeParameters or
kubeObjectSelector. The wizard does not automatically insert a VM recipe.
Inspect the installed DRPC CRD and recipe semantics before protecting a workload.

For the halted diagnostic, Ramen's built-in `vm-recipe` is used. Both DRPC and
RamenConfig need `retainNamespaceSCCAcrossPeers` before creating the secondary
namespace, or restored filesystem access can fail due to differing SCC UID/GID
ranges and SELinux MCS. See [halted diagnostics](halted-vm-protection.md).
This historical partial test is not a running-VM recovery pass.

Workload acceptance requires current-generation protection, disk sync and object
capture timestamps. `PeerReady=True`, DRPC phase alone, or healthy infrastructure
is insufficient. Source isolation must be ownership-guarded and observed before
unplanned promotion. No invented fencing condition or simultaneous writers.

## Evidence scope and implementation references

The historical ARM deployment passed transport, TLS and policy gates, including
a stage-12 zero-change rerun (21 ok, 0 changed, 0 failed). The full historical
rebuild then passed separately. Nested guest execution was blocked; no
running-VM failover passed. See [rebuild evidence](rebuild-validation.md),
[hardware limitations](hardware-blocker.md) and [current validation](current-validation.md).
Current runtime catalog/channel checks are still required: channel heads change.

Policy payload inspection used deployed console image
`registry.redhat.io/odf4/odf-multicluster-console-rhel9@sha256:4685579864d3b0cd0c727c97fae7bc1838920dce59a0d65986e46253ee9f9873`,
source-map module `packages/mco/components/create-dr-policy/utils/k8s-utils.ts`.
The discovered workflow used
`packages/mco/components/discovered-application-wizard/utils/k8s-utils.ts`.
These are versioned implementation observations, not universal API guarantees.

- [MirrorPeer controller](https://github.com/red-hat-storage/odf-multicluster-orchestrator/blob/release-4.22/controllers/odf/mirrorpeer_controller.go)
- [Reference lab's discovered VM setup](https://github.com/shanemcd/ocp-lab/blob/main/docs/odf-ramendr-acm-discovered-vm-setup.md) — do not carry over SINGLE_NODE tweaks or secrets.
- [Acceptance criteria](validation.md) and [operations](operations.md).
