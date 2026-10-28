# Operations and troubleshooting

Start with [getting started](getting-started.md). Retain the same untracked
`local.yml`, inventory, account and release pins for every operation. Examples
below assume the default local workspace paths; substitute your configured paths.

## Observe installation

```sh
virsh -c qemu:///system list --all
sudo tail -n 30 /var/log/libvirt/qemu/dr-hub.serial.log
export KUBECONFIG="$HOME/ocp-install-dr/dr-hub/auth/kubeconfig"
"$HOME/ocp-install-dr/bin/oc" get nodes
"$HOME/ocp-install-dr/bin/oc" get clusteroperators
```

Inspect each cluster's installer directory and its `.openshift_install.log`
locally. Those files may contain sensitive information: redact before sharing.
The installer wait is long-running; an Ansible log with no new lines is not by
itself a failure. Do not run a duplicate stage while the original still runs.
Live ISO installation can reboot guests; transient SSH/API failures are expected.
A kernel marker proves only kernel boot, not API readiness or installation.

`06_install` confirms installer completion, expected node membership and node
Ready state. Compact clusters also require confirmed bootstrap completion before
the role removes their bootstrap domains and load-balancer backends. Do not
manually discard bootstrap state to work around a slow installation.

### Diagnose API discovery timeouts

During bootstrap, ordinary `oc get` can wait on aggregated API discovery even
when core API requests succeed. Use bounded, authenticated direct reads to
separate discovery failure from an unreachable API (same kubeconfig and TLS
verification as above):

```sh
OC="$HOME/ocp-install-dr/bin/oc"
"$OC" get --raw=/readyz --request-timeout=20s
"$OC" get --raw=/apis/config.openshift.io/v1/clusteroperators --request-timeout=20s
"$OC" get --raw=/api/v1/pods --request-timeout=20s
"$OC" get --raw=/api/v1/events --request-timeout=20s
# Substitute an actual node name; the authenticated node proxy avoids SSH key changes.
"$OC" get --raw='/api/v1/nodes/dr-hub/proxy/logs/?query=kubelet&tailLines=200' --request-timeout=20s
```

Keep outputs private and redact before sharing. Check static-pod installer
termination messages and kubelet logs as well as operator conditions. An
installer pod can fail transiently and be reconciled; distinguish continuing
revision progress from a persistent fault. A successful `/readyz` response does
not establish installer completion. Never disable admission, TLS, readiness
checks or fencing to make a stalled installation pass.

## Resume a failed stage

1. Identify the failed task, cluster, resource and literal error.
2. Inspect its events, logs and prerequisites before mutation.
3. Correct the configuration or underlying fault; preserve installer state and
   existing disks. Pass the same overrides to the resumed stage.
4. Re-run the stage's readiness checks and subsequent dependent stages.
5. Record the outcome at the appropriate [validation gate](validation.md).

The playbooks have state and ownership guards, but are not a universal rollback
system. Never rerun ignition generation over a live installation to refresh
credentials. Ignition freshness limits require deliberate rebuild planning.
Never change release pins, disk size, cluster identity, paths or topology beneath
a running lab and expect the next stage to migrate it automatically.

## Common failures

| Symptom | Check and safe response |
| --- | --- |
| CPU capacity assertion | Explicit host CPU-overcommit policy; preserve host headroom and operator guest CPU sizing |
| Disk capacity assertion | Free space and nominal peak disks; smaller **new** test data disks need matching local-volume requests; do not disable the guard |
| `/dev/vhost-net` missing | Host preparation loads `vhost_net` and `tun` persistently; check module availability |
| Artifact checksum mismatch | Architecture/release pins, mirror content and partial downloads; never remove verification |
| No API or application DNS | Lab network, resolver settings, host firewall, DNS and load balancer; do not alter unrelated management networking |
| CSR pending | Inventory node names/IPs and certificate identities; do not bulk-approve unknown CSRs |
| Operator unavailable | Subscription/CSV conditions, deployment events, registry credentials, DNS and node resource pressure |
| PVC pending | StorageClass, LocalVolume device paths, requested size, disk exclusivity and ODF conditions |
| Cross-site timeout | Submariner gateway, routes, firewall and actual application probes; connected status alone is insufficient |
| Remote S3 certificate failure | Trusted service CA, certificate hostname and authenticated endpoint; do not skip TLS verification |
| VMI cannot start | Node allocatable KVM devices, guest architecture/image and VMI events; never bypass admission or enable emulation to claim acceptance |
| Source PVC remains after relocation | VM/VMI and launcher ownership, attachment and finalizers; do not forcibly delete protection while a writer may remain |

## Nested virtualization

Host `/dev/kvm` and enabled CPU nesting flags are necessary but not sufficient.
Check inside an OpenShift node using the generated lab SSH key and normal SSH
host-key verification. Device presence and CPU flags are diagnostic only.
The virtualization stage additionally requires positive allocatable
`devices.kubevirt.io/kvm` on every target node after device-plugin convergence.
A stock VMI must still reach Running/Ready to pass execution acceptance.

The historical ARM failure and exact rejection messages are preserved in
[hardware limitations](hardware-blocker.md). That report does not describe
current x86_64 readiness.

## Optional running-guest fixture

After infrastructure, storage and virtualization gates pass:

```sh
ansible-playbook shanemcd.dr_lab.provision_running_vm -e @local.yml
```

This deliberately **one-time** provisioner refuses an existing fixture namespace
on either site. On a partial failure, inspect and repair existing resources;
do not delete a protected/recovered namespace merely to rerun provisioning.
The default `dr-running-vm/fedora-dr` uses a native digest-pinned Fedora 44
container disk imported by CDI to a 20 GiB RBD filesystem PVC. Both architecture
pins are in `inventory/group_vars/all/workload.yml`. This community test guest
is not a production guest support claim. The VM boots from the PVC, not a
containerDisk; the DataVolume only imports the initial image. The VM and actual
PVC receive the Ramen selection label; no protection is implicitly requested.

The gate requires VMI Running, Ready and AgentConnected. It does **not** prove
guest data recovery. Cloud-init installs the guest agent and authorizes only the
lab SSH public key for `labuser` (password login disabled); it intentionally
never creates a data marker. Write and fsync a unique marker from an authenticated
guest session **after** first boot, record its hash and write time outside the
guest, then capture Ramen disk and object checkpoints before recovery. Recovered
verification must read the existing marker without recreating it. Use the
matching OpenShift Virtualization `virtctl` release with normal guest SSH host
verification, not a privileged host mount of the replicated disk.

### Obtain the matching guest-access client

Read `oc get consoleclidownloads -o yaml` on an installed virtualization target.
Select the `virtctl` link for the **controller's** OS/architecture; do not assume
that the OpenShift release number equals the KubeVirt client version. Use the
operator-published HTTPS endpoint rather than an arbitrary upstream binary.
For the default ingress certificate, obtain the router CA through the already
trusted, authenticated API:

```sh
"$OC" get secret router-ca -n openshift-ingress-operator \
  -o 'jsonpath={.data.tls\\.crt}' | base64 -d > /tmp/dr-lab-router-ca.crt
# Set URL to the matching ConsoleCLIDownload link inspected above.
curl --fail --cacert /tmp/dr-lab-router-ca.crt "$URL" -o /tmp/virtctl.tar.gz
tar -tzf /tmp/virtctl.tar.gz
```

Inspect the archive, extract `virtctl` into a local tools directory and record
its hash and `virtctl version --client`. If using a custom ingress certificate,
use its trusted CA instead. If wildcard application DNS is unavailable on the
controller, repair DNS or use curl `--resolve HOST:443:IP` with a verified
inventory ingress-node address, retaining the URL hostname and CA verification.
Never use `--insecure`. Client acquisition is not a guest-execution test.

After recording the durable guest marker, request **initial protection**:

```sh
ansible-playbook shanemcd.dr_lab.protect_running_vm -e @local.yml
```

This separate step requires a Running/Ready/AgentConnected source VMI, a bound
selected disk, namespace SCC retention enabled and no existing peer namespace,
matching DRPC or placement. It never changes an existing recovery action or
creates guest data. A partial failure requires inspection; do not blindly rerun
or remove controls. The gate requires generation-current `Protected=True`,
`lastGroupSyncTime` and `lastKubeObjectProtectionTime`; inspect actual disk and
object captures and confirm their times postdate the marker before recovery.
These checkpoints alone are not recovered-guest integrity proof. There is no
automatic fencing, relocation or failover in either fixture playbook.

The fixture has offline rendering/safety tests and x86_64 live execution,
protection and assisted recovery evidence in [current evidence](current-validation.md).
The observed Ramen/Velero combination required manual metadata import for every
recovery. Read the [compatibility limitation and assisted procedure](compatibility.md)
before planning a test; this is not an unattended-recovery claim.

## Recovery safety

Before unplanned failover, establish source-site isolation and preserve evidence
that no source VM can write. Do not invent a fencing status, delete storage
finalizers to force promotion, or start the same disk at both sites. Use the
installed product's supported recovery procedure and stop if its preconditions
are not met. Planned relocation, halted diagnostics and unplanned failover are
different tests. Verify guest data and measure RPO/RTO, not just DRPC phase.

### Single-host disaster simulation boundary

This topology puts both sites on one physical host. Stopping the source site's
OpenShift domains simulates loss of that site, **not** independent physical
failure domains or loss of the shared host. Record this limitation with results.
Before using a manual-fencing procedure:

1. Derive the complete source node list from the same inventory used to deploy.
   Match each domain's UUID against the inventory-generated UUID (`node.name |
   to_uuid`), inspect its disk paths and confirm source-cluster membership.
   Do not infer ownership from a domain name alone. Check that no bootstrap
   domain or alternate source-node domain remains running.
2. Record UTC time, UUIDs, current domain states, autostart settings and every
   other restart mechanism (including active Ansible jobs). Disable autostart
   only for the verified source domains and stop any lab reconciliation that
   could restart them. Do not run `05_snos`, `core` or `site` during isolation.
   This is not sufficient protection against a host reboot unless all restart
   mechanisms have been accounted for; abort if they cannot be controlled.
3. Power off **all** verified source cluster domains, not only the node that
   currently hosts the VMI. Confirm each is shut off and remains so. Save host
   observations outside Git; failed API probes alone are not fencing evidence.
   The destination and hub must remain running. Do not attach source disks to
   diagnostic writer VMs or pods.
4. Only after isolation is established, follow the installed ODF/Ramen version's
   manual-fencing and failover procedure. A controller status flag records an
   externally established fence; it does not create one. Retain the fence until
   the documented rejoin/demotion procedure makes source restart safe.
5. Verify the target VMI is Running, Ready and AgentConnected, then read the
   original guest marker using authenticated guest access. Never recreate the
   marker, reprovision the VM, or mount a replicated disk on the host to satisfy
   this check. Validate the recovered hash against the separately saved source
   hash. A DRPC phase alone does not establish data integrity or single-writer
   safety.

Record at least marker write/fsync time, last disk and object checkpoints,
fence start and confirmation, failover request, controller completion, recovered
VMI readiness and successful guest read. Report controller recovery duration
separately from end-to-end RTO (fault injection to verified guest data). A single
pre-fault marker proves only that this marker survived; it does **not** establish
a numerical maximum RPO for ongoing writes. For measured RPO, use timestamped,
fsynced sequential records and compare the last acknowledged source record with
the recovered prefix. Planned failback needs a new unique durable target marker,
final synchronization, exclusive disk roles and a verified read at the original
site. Restore autostart only after safe rejoin and record its final state.

## Cleanup

Review the teardown role before invoking it. It destroys the selected lab's
resources and disks; it does not revert every host package or configuration.
Keep local credentials out of Git throughout cleanup. Ownership guards protect
against unrelated same-name domains, not against incorrect lab configuration.

A bare run removes the lab VMs, network, artifacts and install data. It does
**not** uninstall ACM or virtualization through cluster APIs before destroying
the VMs. To uninstall those layers separately while clusters are still running,
run `--tags acm` and then `--tags virtualization` first; do not combine those
tags with `vms` (the in-cluster uninstalls are deliberately skipped in that case).
Tagged layer operations do not remove every other layer automatically.

```sh
ansible-playbook shanemcd.dr_lab.teardown -e @local.yml
```

Before any layer (including tagged runs and check mode), a read-only path guard
rejects noncanonical paths, symlink components, overlapping deletion trees and
resource names containing path separators. `vm_assets_dir` and `install_base_dir`
must be distinct dedicated directories beneath `lab_user_home`, `/srv`, `/mnt`,
`/data` or `/opt`; neither may contain the home directory, repository playbooks,
SSH directory or configured pull secret. Independently removed workspace subtrees
must be distinct, nonoverlapping children of `vm_assets_dir`.
`libvirt_runtime_dir` must be a dedicated child of `/var/lib/libvirt/images`, and
`loadbalancer_state_dir` a dedicated child of `/etc/dr-lab`. Defaults satisfy these
restrictions; deployments using other layouts must be reviewed before cleanup,
not bypass the guard. This is configuration validation, not proof that every
file belongs to the lab, and does not eliminate filesystem races.

Never run teardown while another deployment or recovery operation is active.
Do not change configured paths, symlinks or directory contents during cleanup.
Do not skip the `always` tag: it carries both path and libvirt preflight checks.
