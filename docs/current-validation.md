# Current portability deployment evidence

This report covers the x86_64 deployment and assisted recovery validation on
2026-10-28, including final read-only checks at 19:22 UTC. It is separate from
the historical ARM [rebuild report](rebuild-validation.md). The demonstrated
result is manually assisted recovery, not unattended compatibility.

## Environment and configuration

RHEL 10.2, x86_64, 64 logical CPUs, host KVM available with Intel nesting
enabled. The installation uses the pinned OpenShift 4.22.16 release, native KVM,
UEFI and host-passthrough CPUs. Software emulation is disabled.

Local sizing overrides: CPU overcommit ratio 3.0, six 100 GiB ODF data disks,
and 99 GiB local volume requests. All root disks, memory allocations and host
headroom checks retain their defaults. This is small-capacity test storage, not
a production sizing recommendation. The default topology still requests 140
vCPUs and 312 GiB during installation, including two bootstrap guests.

## Observed results

| Gate | Result |
| --- | --- |
| Offline unit tests | 46 passed (including local Markdown file links and default inventory selector/address consistency), including native/cross-architecture preflight, configuration/KVM gates, running-fixture rendering, reseeding, initial-protection guards, safe workspace handback, credential Git exclusions, shell boundaries, fail-closed operator queries, tagged NTP cleanup and read-only teardown path guards, pre-staging VM ownership and explicit uninstall-tag selection |
| Site syntax on Ansible Core 2.19.14 | Passed |
| `01_host_prep` | Passed, including capacity, device and nested-flag preflight |
| `02_artifacts` | Passed, pinned downloads verified |
| `03_network` | Passed, 33 tasks, zero failures; API/application DNS checked |
| `04_ignition` | Passed, 156 tasks, zero failures |
| `05_snos` | Passed, 130 tasks, zero failures; all nine domains running and kernel markers observed |
| `06_install` | Passed by 16:48 UTC: 71 tasks, zero failures/ignored; all three installer completion and inventory Ready/schedulable node gates passed; both owned compact bootstrap domains removed |
| `07_virtualization` | Passed by 16:56 UTC after correcting quantity parsing: 34 tasks, zero failures/ignored; both CSVs Succeeded, HCOs Available, 25 deployments ready per site, native configuration and positive KVM on all six nodes |
| `08_acm` | Passed by 17:05 UTC: 26 tasks, zero failures/ignored; MultiClusterHub Running, both spokes Available and all five configured add-ons Available per spoke |
| `09_storage` | Passed by 17:24 UTC: 52 tasks, zero failures/ignored; both sites passed StorageCluster, Ceph, dynamic RBD and NooBaa/bucket gates |
| `10_submariner` | Passed by 17:27 UTC: 58 tasks, zero failures/ignored; bidirectional remote pod/service data and authenticated verified-TLS S3 PUT/GET/DELETE passed |
| `11_dr_prerequisites` | Passed by 17:34 UTC: 99 tasks, zero failures/ignored; GitOps, OADP, orchestrator, DR APIs and hub operator gates passed |
| `12_regional_dr` | Passed by 17:37 UTC: 29 tasks, zero failures/ignored; policy/DRCluster validation, peering, namespace mirroring and object trust gates passed |
| Nested workload guest execution | Passed by 17:40 UTC: PVC-backed Fedora x86_64 VMI Running/Ready/AgentConnected; authenticated guest SSH and agent service active |
| Initial protection and checkpoints | Passed by 17:43 UTC: generation-current Protected=True, selected root PVC, disk and object checkpoint timestamps after fsynced marker |
| Planned relocation and recovered guest integrity | Passed with manual Velero metadata-import assistance; not unattended recovery |
| Physically fenced failover and failback | Original marker verified after assisted failover and assisted planned return to the pre-outage active site; guarded rejoin, unfencing and generation-current protection passed. Metadata import remains manual, not unattended recovery |

At 16:06 UTC all three nodes on each compact cluster were Ready. Hub `/readyz`
passed, but multiple operators remained unavailable and normal CLI discovery
intermittently timed out; direct authenticated API reads still worked. At
16:07 UTC static-pod installers showed API request timeouts and the kubelet
reported mirror-pod admission timeouts. Without intervention, by 16:09 UTC
hub etcd, kube-apiserver and kube-scheduler were Available, discovery returned
node status normally, and most operators were Available. Controller-manager,
authentication, console and other operators were still converging; machine-config
reported Degraded. By 16:11 UTC machine-config was no longer Degraded and
openshift-apiserver and samples were Available. Controller-manager was still at
revision 0, its operator waiting for leader election; authentication, console
and monitoring remained pending. At 16:13 UTC the hub console showed boot into
the newer CoreOS deployment; by 16:16 UTC controller-manager was fully Available
and no longer Progressing. Authentication, console and monitoring were still
pending. Monitoring became Available at 16:17 UTC. After a transient API refusal
during a static-pod revision transition, hub authentication and console became
Available and the installer confirmed completion at 16:21 UTC (31m14s). Primary
installation and inventory node checks passed at 16:22 UTC; its bootstrap domain
was removed by the ownership-guarded installer role.

The same stage then waited on recovery bootstrap. At 16:22 UTC its three
nodes were Ready, but etcd and kube-apiserver remained at revision 0 with no
static pods in their namespaces. Etcd operator could not persist observed
configuration because of repeated resource-version conflicts. After confirming
only one operator replica, its deployment was restarted at about 16:23 UTC to
reset controller caches. Observed TLS configuration then persisted and revision 1
was created; no TLS values or security controls were manually changed. By
16:29 UTC two etcd operands were 5/5 Running and the first kube-apiserver operand
was 5/5 Running. Etcd, kube-apiserver and kube-controller-manager reported
Available, but rollout and bootstrap completion were still pending. This was a
manual recovery action, not an unattended installation result.

By 16:36 UTC recovery bootstrap completed and the ownership-guarded role removed
its bootstrap domain. All three etcd and all three kube-apiserver operands were
5/5 Running. The installer moved to its final completion gate. Router pods had
failed startup while waiting for the Route API; both became 1/1 Running by
16:38 UTC without intervention. Authentication, console, ingress operator status
and monitoring were still converging. Ingress and monitoring became Available
by 16:39 UTC, console by 16:41 UTC and authentication by 16:47 UTC. Final
API-server rollout converged and stage `06_install` passed by 16:48 UTC. Stage
`07_virtualization` then started. Its first run exposed a gate bug: the API
serializes 1,000 KVM devices as `1k`, which an integer cast incorrectly treated as
zero. The read-only wait was stopped, the parser corrected and regression cases
added. A full rerun passed by 16:56 UTC, including native execution configuration
and positive allocatable KVM on all six nodes. No emulation or cluster setting
was changed. Stage `08_acm` then started.

The operator-published Linux/amd64 `virtctl` client was downloaded with the
router CA obtained through the authenticated API. Controller wildcard DNS was
unavailable, so curl used a verified primary inventory ingress-node address via
`--resolve`, retaining hostname and CA verification. The client reports v1.8.4;
SHA-256 `1f5c8f5c24b3da929e46e11d82f5f5fefceb543125a9926df8196f92acfd40cc`.
Acquiring a client is not evidence of guest execution.

No readiness/security gate was skipped. The three-cluster core installation gate
has now passed, including the manual controller recovery described above. This
is not evidence of full downstream operator readiness or running-workload DR.

Stage `08_acm` converged without manual intervention: the installed hub version
is 2.17.3 on channel `release-2.17`. Both managed clusters became Available;
`work-manager`, `cluster-proxy`, `search-collector`,
`governance-policy-framework` and `config-policy-controller` became Available on
each spoke. Stage `09_storage` started at 17:04:44 UTC. By 17:14 UTC primary
StorageCluster readiness, Ceph `HEALTH_OK`, dynamic RBD PVC binding, NooBaa
readiness and dynamic bucket/credential gates passed. At 17:17 UTC recovery
StorageCluster was Progressing (age 79 seconds), with Ceph detecting its version.
By 17:24 UTC recovery passed the same storage gates and the stage completed
with zero failures. No manual intervention was required. These readiness and
provisioning tests do not demonstrate replicated workload data.

Stage `10_submariner` then completed by 17:27 UTC. Both sites exchanged the
expected application payload directly with remote non-hostNetwork pods on
non-gateway nodes and with their remote service IPs. Both directions also passed
S3 PUT/GET/DELETE with issued credentials and verified TLS. This demonstrates
application transport and object connectivity, not VM replication or failover.
Stage `11_dr_prerequisites` started at 17:27 UTC and passed by 17:34 UTC.
It retained existing proxy trust while adding the site ingress CAs, then verified
GitOps, OADP and orchestrator prerequisites and the DR hub APIs/operator.
Stage `12_regional_dr` passed by 17:37 UTC: DRPolicy and both DRClusters validated,
StorageClusterPeers became Peered, and namespace-level daemon/image/group
mirroring health was OK on both sites. Documented Ramen object-backup trust
propagated normally. No manual intervention or security bypass was used in
these stages. Healthy empty mirroring infrastructure is not workload data proof.

The optional `provision_running_vm` completed by 17:40 UTC: 15 tasks, three
changes, zero failures/ignored. The imported Fedora boot disk is a filesystem
RBD PVC; `fedora-dr` became Running/Ready/AgentConnected on `dr-primary-m3`.
Authenticated key-only guest SSH confirmed x86_64 and active qemu-guest-agent.
A unique marker was created exclusively (never overwritten), then file and
directory fsynced at `2026-10-28T17:40:45.068522+00:00`. SHA-256:
`21613b6bf29a4c8d85ec138fde47305df240fe1a71f972cc7fbaf6e408a89f94`.
Cloud-init does not create this marker.

Initial `protect_running_vm` then passed by 17:43 UTC: 19 tasks, one change,
zero failures/ignored. DRPC generation 2 is Deployed/Completed and Protected=True
at observedGeneration 2. Its protected PVC list includes `fedora-dr-root`;
`lastGroupSyncTime=2026-10-28T17:41:03Z` and
`lastKubeObjectProtectionTime=2026-10-28T17:41:16Z`, both after the guest write.
The asynchronous resource condition DataProtected was False/Replicating while
the top-level Protected condition was True. These are reported controller
checkpoints, not yet proof of recovered guest bytes, ongoing-write RPO or RTO.
Planned relocation was requested at `2026-10-28T17:44:34.582979+00:00`.
Ramen paused at `WaitOnUserToCleanUp` because the selected PVC is not fully
VM-owned. After verifying exact fixture identity, the source VM was halted,
its VMI disappearance and absence of live PVC-consuming pods verified, and only
the fixture VM/DataVolume were deleted with UID preconditions. The PVC entered
normal deletion through garbage collection; replication finalizers were not
removed. Source VRG reached Secondary. The controller reported Relocated/Completed
with `actionDuration=3m57.201428784s` at 17:48:31 UTC, but by 17:52 UTC the
destination had only the PVC, not a VM/VMI. KubeObjectsReady=False reported
restore errors, and Protected=False reported a VM-selector mismatch. Velero
also logged `backup already exists in object storage`. Read-only authenticated
S3 inspection subsequently confirmed both stores retain the original `Completed`
backup metadata (three items, completed at 17:41:12/17:41:16 UTC) and archives
containing the namespace, VM and VMI definitions. Destination Ramen creates a
placeholder Backup that Velero marks Failed because the name already exists in
S3; its Restore then enters FailedValidation with `backup ... is in phase
"Failed" and cannot be used as a restore source`. This repeats without restoring
the VM. Installed components are OADP 1.6.2, Velero
`v1.18.2-rc.2-OADP` and ODR `4.22.6-rhodf`. A supported recovery path for this
controller interaction was not available through the automatic flow. No S3
objects or checkpoints were deleted or status fields forged.

Recovery required manual assistance: the destination Ramen deployment was
scaled from one replica to zero after confirming neither site had a VMI. The
FailedValidation Restore and Failed placeholder Backup CRs were removed with
UID preconditions and normal finalizers. A separate temporary read-only BSL
pointing at the original backup prefix let Velero natively import the original
Completed backup metadata. Resuming Ramen restored the VM; no VM definition was
manually applied and no guest data was reseeded. The temporary BSL was removed
afterward and diagnostic logging restored to its default.

The destination VMI became Running/Ready/AgentConnected. At
`2026-10-28T18:02:04.998588+00:00`, SSH with the original recorded host key and
strict verification read the original marker with its expected SHA-256. This
proves **manually assisted planned relocation and recovered marker integrity**.
The observed request-to-successful-marker-read interval was about 17m30s,
including troubleshooting and client setup—not an unattended RTO benchmark.
DRPC generation 3 then reported Relocated/Completed, Available/PeerReady/Protected
True, with disk/object checkpoints at 17:58:01/18:01:14 UTC. A single marker does
not establish ongoing-write RPO. At this point physically fenced failover and
failback had not run; the subsequent failover result is recorded below. The controller interoperability problem remains a reproducibility
limitation despite this successful assisted recovery.

The lab guests running in libvirt are the OpenShift nodes, not the recovered VM
workload. Kernel boot markers are not evidence of cluster readiness or DR.
Installer completion and downstream gates must be recorded before making any
stronger claim. Follow [validation criteria](validation.md).

Raw local logs and installer state are intentionally not checked into Git;
they can contain credentials. Do not publish ignition, kubeconfigs or unredacted
installer output with this report.


## Physically isolated failover attempt

At 18:03 UTC the active site was `dr-recovery`, with its guest Running, Ready
and agent-connected, generation-current protection and an object checkpoint at
18:02:52 UTC. The target `dr-primary` namespace had no VM/VMI/PVC. After matching
all three recovery master-domain UUIDs to inventory-derived identities and
checking their dedicated root/data disk paths, autostart was disabled and all
three domains were powered off through libvirt. All were confirmed shut off at
`2026-10-28T18:03:49.377884+00:00`. No active provisioning/reconciliation job or
scheduled lab restart was found. The hub and primary domains remained running.
This is a site-domain outage simulation on one physical host, not independent
physical fault domains.

Only after that confirmation, the recovery DRCluster was set ManuallyFenced
and Failover to primary was requested at 18:03:55 UTC. The hub confirmed Fenced
at generation 2. Its S3 validation subsequently failed because the powered-off
site endpoint was inaccessible, as expected. By 18:05:31 UTC DRPC generation 4
reported FailedOver, but its progression remained Cleaning Up: the primary PVC
was Bound and the VRG Primary, with no restored VM/VMI. Velero again reported
`backup already exists in object storage` for Ramen placeholder Backups and
kube-object restore failed. This repeats the compatibility failure diagnosed
during planned relocation; controller FailedOver is **not** recovered-guest
success at that point.

Primary-site Ramen was then paused while only Failed fixture placeholder Backup
CRs and FailedValidation Restore CRs were removed with UID preconditions and
normal finalizer handling. A separate read-only BSL allowed Velero to import
the original Completed metadata from the surviving primary object store.
No S3 backups were changed or deleted; no status was forged and no VM was
manually reconstructed. After Ramen resumed, the restored guest became Running,
Ready and AgentConnected. Strict SSH using the original recorded host identity
verified the original marker SHA-256 at
`2026-10-28T18:09:03.865721090+00:00`.

Request-to-verified-guest time was approximately 5m09s; physical-fence-confirmation
to verified guest was approximately 5m14s. These are manually assisted recovery
measurements, including metadata-import diagnosis and client time, **not an
unattended RTO**. The last reported pre-fence object checkpoint (18:02:52 UTC)
was about 57 seconds before physical isolation; this is metadata age, not a
measured ongoing-write RPO. The single durable marker survived both relocation
and this failover; no continuous-write loss bound has been established.

The temporary import BSL was removed and primary Ramen is running normally.
KubeObjectsReady and NoClusterDataConflict are now True. Protected remains False
while the peer site was off and its object endpoint was inaccessible; this is not
a restored redundancy claim. The original guest marker must not be recreated.

### Guarded control-plane rejoin (in progress)

Before restarting any recovery domain, all three dedicated Ceph data disks
were detached from their inactive libvirt definitions, after UUID/path and
shut-off/autostart-disabled checks. Every data disk was confirmed absent before
any domain started and again from the live definitions. Autostart remains
disabled and the DRCluster manual fence remains set. This lab-specific storage
isolation allows control-plane cleanup without exposing the old replicated
volume; it is not a general production rejoin recipe or a completed unfence.

All three nodes returned Ready. Cached VM/VMI Running status initially survived
the outage, but the launcher pod was failed and storage was physically absent;
that cached status is not evidence of a second running guest. The first UID/RV-
guarded Halted patch was rejected because the kubemacpool admission webhook had
no endpoints. After normal convergence (90 seconds), the unchanged security
checks allowed the patch. The old VM is now Halted, its VMI is absent and no
namespace pod consumes its PVC. No webhook or finalizer was bypassed.

The pending VolumeAttachment was investigated before storage return. Its normal
detach request was already in progress. Read-only node inspections on all three
nodes found no RBD devices, RBD mounts, guest QEMU processes or virt-launcher
processes. The VRG in `openshift-dr-ops` (not the workload namespace) requested
Secondary and reported manual resource cleanup necessary. The stale fixture VM
and PVC were therefore deleted with UID preconditions and normal finalizers.
Only after no VM/VMI/PVC-consuming pod remained and the PVC had a deletion
request were the original data-device XML definitions reattached to the exact
owned domains, live and persistent. No replicated role or finalizer was forced.

After two real 120-second waits, recovery Ceph returned Ready/HEALTH_OK and the
old workload VolumeAttachment disappeared normally. At 18:20 UTC redundancy
was not yet restored: although VolumeReplication displayed `Secondary`, its
Completed condition was False with `FailedToDemote`; the VRG remained Unknown.
CSI reported that the volume-group member image could not be found (`rbd:
ret=-2, No such file or directory`). That summary state alone was not successful
demotion/resynchronization proof.

No image/group/trash cleanup, role forcing or controller restart was needed.
By 18:22 UTC the original RBD image and group existed, trash was empty, and
mirroring showed recovery replaying from the primary. The error transitioned
to missing local snapshot time during initial resync, then cleared normally.
After real 120- and 180-second observation intervals, the stale VM/VMI/PVC were
absent, the secondary VRG reported cleanup Completed, and the hub reported
PeerReady=True. At 18:27:32 UTC DRPC generation 4 reported Protected=True at
observedGeneration 4, disk checkpoint 18:24:00 UTC and object checkpoint
18:27:29 UTC. Both Ceph clusters reported HEALTH_OK. RBD per-image/group status
showed the primary writable and recovery replaying; the manager identity could
not query daemon-service health, so its aggregate UNKNOWN is not a daemon-health
pass. Strict SSH on primary also verified the original marker unchanged during
this iteration. These are refreshed protection/checkpoint and marker-survival
evidence, not a new failback or an ongoing-write RPO measurement.

At 18:30 UTC, after verifying generation-current protection/peer readiness,
secondary cleanup, no recovery VM/VMI/PVC consumers and a Ready/agent-connected
primary guest, the DRCluster was changed to `ManuallyUnfenced` with a
resourceVersion precondition. The hub confirmed generation 3 Unfenced,
Clean=True and Validated=True. Recovery-domain autostart remains disabled.

### Planned return after rejoin (manually assisted)

A planned return to `dr-recovery` (the active site immediately before the
outage) was requested at 18:31 UTC using Relocate, not another forced failover.
Generation 5 paused at `WaitOnUserToCleanUp`, with source VRG desired Secondary
and AutoCleanup=False/NotFeasible. Only the selected fixture VM was halted;
after its VMI disappeared and no pod consumed its PVC, the VM and PVC were
deleted with UID preconditions and normal finalizers. No guest was reseeded or
replicated role forced.

By 18:35:57 UTC the controller reported Relocated/Completed and PeerReady=True.
At 18:36 UTC recovery had a Bound PVC but no VM/VMI; primary had no VM/VMI and
its old PVC was still terminating normally. Protected remained False due to
missing VM-selection matches. Velero again logged `backup already exists in
object storage`. At that point the controller Completed result did not prove
successful running-guest failback.

The same scoped native metadata-import assistance was then required on recovery.
With neither site hosting a VM/VMI, recovery Ramen was paused; only Failed
fixture Backup and FailedValidation Restore CRs were removed with UID
preconditions and normal finalizers. A temporary read-only BSL used capture 1
in the original primary backup store. Velero natively imported its Completed
metadata, then Ramen was resumed. No S3 content, backup status, VM definition
or guest data was manually rewritten. The temporary BSL was removed afterward;
Ramen returned to one available replica.

By 18:41:46 UTC the returned VMI was Running/Ready/AgentConnected. Strict SSH
with the original recorded host key read the original marker at
`2026-10-28T18:41:51.615450491+00:00`, with the same SHA-256 documented above.
Request-to-marker time was about 10m37s, including manual diagnosis/import and
observation delay, **not an unattended RTO**. DRPC generation 5 reported
Relocated/Completed and Available/PeerReady/Protected=True observedGeneration 5,
with disk checkpoint 18:39:00 UTC and object checkpoint 18:41:05 UTC. The old
primary VRG was Secondary with cleanup Completed. Recovery's asynchronous
DataProtected condition still reported False/Replicating, while
ClusterDataProtected and KubeObjectsReady were True.

This demonstrates an assisted planned return to the site active immediately
before the outage, with original marker survival and refreshed protection. It
does not establish maximum ongoing-write RPO, independent physical failure
domains, or unattended reproducibility. Recovery node-domain autostart remains
disabled from the fence exercise. The Ramen/Velero compatibility limitation and
final public usability/security/reproducibility audit remain open.

### New-write failback check (passed with manual assistance)

The assisted return above verified the original marker but did not test recovery
of a new post-recovery write. To exercise that stronger criterion, a **separate**
marker was created exclusively on the recovery-site guest and file/directory
fsynced at `2026-10-28T18:43:40.489583+00:00`. Its SHA-256 is
`b375e5306404f62857b6ba4b4a5010c4b7154a40569e5f74a02e3116a56c60f5`.
The original marker was not overwritten, and cloud-init does not generate either.
After real observation waits, disk checkpoint 18:44:00 UTC and object checkpoint
18:47:10 UTC were both newer than the acknowledged write; generation 5 remained
Protected/PeerReady=True. Checkpoints alone do not prove recovered bytes; the subsequent guest read below does.

A planned Relocate to the initial `dr-primary` site was then requested with a
resourceVersion precondition after verifying the live recovery guest, empty
primary workload namespace, secondary cleanup and clean/validated unfence.
The DRPC `preferredDecision` still named primary from earlier history; current
site identification instead used the requested site, live VMI and both VRG
roles, not that stale field. Generation 6 reached Relocating/
WaitOnUserToCleanUp by 18:52 UTC. Source cleanup then used resourceVersion-guarded
Halted and normal UID-scoped VM/PVC deletion only after the VMI and all PVC
consumers were absent. No finalizers or replication roles were forced.

Controller Relocated/Completed at 18:55:02 UTC (duration 5m04.917s) again preceded
usable guest recovery: primary had no VM and Velero rejected Failed placeholder
backups. The same scoped, temporary read-only native metadata import from recovery
capture 1 was required; only primary Ramen was paused and then resumed. No S3
mutation, forged status, manual VM reconstruction or marker reseeding occurred.

By 18:59:40 UTC the primary VMI was Running/Ready/AgentConnected. Strict SSH using
the original host identity verified **both** the original SHA-256 above and the
new `b375e530…a56c60f5` hash. Request-to-guest-read was approximately 9m42s,
including manual import and observation, **not unattended RTO**. This proves
survival of the separate post-recovery write, not maximum ongoing-write RPO.
The temporary import location was removed normally. Generation 6 had
Available/PeerReady/Protected=True observedGeneration 6, disk checkpoint
18:54:58 UTC and object checkpoint 18:59:01 UTC. Primary had one VM/VMI/PVC;
recovery had none, so obsolete source workload cleanup was confirmed. Resource
DataProtected=False/Replicating still coexisted with top-level Protected=True.
Recovery domain autostart remains disabled; DRCluster remains ManuallyUnfenced.
All 29 unit tests and diff whitespace checks passed at that recovery checkpoint.
The final scoped review and later test results are recorded below; the unattended
compatibility limitation remains unresolved.

## Final read-only confirmation and review

At 19:22 UTC, generation 6 remained Completed with Available, PeerReady and
Protected all True at observedGeneration 6. Disk/object checkpoints had advanced
to 19:19:01/19:19:55 UTC. Primary had exactly one fixture VM, VMI and PVC;
recovery had none and its VRG was Secondary. Primary VMI remained Running,
Ready and AgentConnected. Both Ramen deployments had one available replica;
neither site retained the temporary metadata-import BSL.

At 19:22:07 UTC, strict SSH with the original recorded guest host key read both
marker files again, matching the full hashes recorded above. No marker was
created or changed and no guest relocation or cluster mutation was performed.
All seven remaining node domains were running; the two bootstrap domains were
absent. Recovery-domain autostart remains disabled intentionally, so a host
restart requires an operator-reviewed startup plan. This final inspection does
not add another recovery trial or establish ongoing-write RPO.

Final validation: **46 unit tests passed**, offline Ansible lint met the
production profile (169 files, zero failures/warnings), scoped YAML lint passed,
and site, teardown, provision-running-VM and protect-running-VM syntax checks
passed. The offline dependency-install skip notice is expected. All 173 owned
candidate files were included in the final inventory. Public configuration,
shell/deletion safeguards, documentation links and credential exclusions were
reviewed with targeted regression coverage; this is not a formal security audit.
A limited private-key/auths signature scan found no candidate matches. Raw API
snapshots and guest reads remain outside Git in a mode-0700 evidence directory,
with the new final records mode 0600; credentials and raw logs are not published.
The reference `ocp-lab` working tree is unchanged. Changes in `dr-lab` are left
uncommitted for review, including new files; no commit or push was performed.

The requested native portability implementation, public documentation and
**live assisted running-VM failover plus post-recovery-write return** have been
demonstrated. Remaining boundaries are explicit: ARM runtime is unvalidated,
these sites share a physical host, maximum ongoing-write RPO was not measured,
operator channels roll, and the installed Ramen/Velero restore combination
still needs the documented manual metadata-import assistance. No unattended,
vendor-supported automatic recovery or fresh-host reproducibility is claimed.
See [compatibility](compatibility.md) before deploying or recovering workloads.
