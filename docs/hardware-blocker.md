# VM execution capabilities and validation limits

## Historical ARM deployment (not the current host)

This report records the previous Ampere Altra experiment. The current native
x86_64 deployment is tracked in [current validation](current-validation.md).
The portable inventory now disables software emulation by default and host
preflight rejects it for DR acceptance. Commands and image digests below are
historical reproductions, not instructions for the current deployment.

The previous compact-cluster rebuild comprised one ACM hub and two three-master
OpenShift 4.22.16 ARM64 clusters. Both sites passed standard ODF provisioning,
Submariner application traffic, authenticated remote S3 with verified TLS,
and current ODF Regional-DR peering/policy gates. A full teardown and single
untagged infrastructure redeployment subsequently passed on 2026-10-28; see
[rebuild validation](rebuild-validation.md). Neither infrastructure checks nor
that rebuild establish successful VM execution or running-VM recovery.

The physical host is Ampere Altra Q80-30 / Neoverse-N1, aarch64. Its OpenShift
nodes are first-level KVM guests. All primary nodes advertise
`devices.kubevirt.io/kvm: 0`; their guest `/dev/kvm` is absent.

The physical-host capability probe:

```sh
timeout 5 qemu-system-aarch64 -accel kvm -machine virt,virtualization=on \
  -cpu host -m 128 -nodefaults -display none -S
```

exited immediately with code 1:

```text
qemu-system-aarch64: mach-virt: host kernel KVM does not support providing Virtualization extensions to the guest CPU
```

Adding masters or memory cannot fix this limitation. ARM64 product availability
is not evidence of nested-virtualization capability on this CPU.

## Explicit upstream software-emulation experiment

After the historical cluster/storage/DR infrastructure gates passed, an
explicit emulation experiment selected `virtualization_use_emulation: true`.
This is no longer the inventory default or an accepted execution path. It feeds `KVM_EMULATION` through the OLM Subscription's
`spec.config.env`, the upstream HCO documented installation path. HCO itself
owns and reconciles the resulting KubeVirt configuration. The lab does not
patch a CSV, operator Deployment, KubeVirt CR or unsupported-config annotation.

Upstream source references (inspected commit
`54c05719dc6375c8e0099323aaf90e91428ce8d8`):

- [HCO installation guide, KVM Emulation](https://github.com/kubevirt/hyperconverged-cluster-operator/blob/54c05719dc6375c8e0099323aaf90e91428ce8d8/deploy/kustomize/README.md)
- [Subscription environment overlay](https://github.com/kubevirt/hyperconverged-cluster-operator/blob/54c05719dc6375c8e0099323aaf90e91428ce8d8/deploy/kustomize/kvm_emulation/subscription.patch.yaml)
- [HCO handler](https://github.com/kubevirt/hyperconverged-cluster-operator/blob/54c05719dc6375c8e0099323aaf90e91428ce8d8/controllers/handlers/kubevirt.go): reads `KVM_EMULATION` and sets `developerConfiguration.useEmulation`.

This is an explicit upstream lab mode, **not** a claim of Red Hat support for
software-emulated ARM64 VMs or single-host virtualized Regional DR. Until tested,
even successful acceptance of the environment variable is not proof that the
shipped ARM64 QEMU can execute a VM. A restricted, non-root capability pod using
the deployed virt-launcher image (`registry.redhat.io/container-native-virtualization/virt-launcher-rhel9@sha256:2131d3d24616971b92d7e986635673b6dc731da3d43cae46540882993d36596f`)
reported `aarch64`, QEMU `10.1.0 (qemu-kvm-10.1.0-17.el9_8.5)`, and accelerators
`kvm` and `tcg`. This establishes that TCG is compiled in, not successful VM boot. The user only requires a minimal running VM,
not a substantial workload. Actual target VMI execution and protected state must
be observed; operator availability alone is insufficient.

## Live ARM64 emulation attempt: blocked

Both sites installed OpenShift Virtualization 4.22.12 normally (25 ready
Deployments per site). The explicit emulation rerun passed with HCO-owned
`developerConfiguration.useEmulation: true` observed on both sites. Neither
result proves an executing VM.

The reproduction manifest is [evidence/arm64-emulation-smoke.yaml](evidence/arm64-emulation-smoke.yaml).
Create namespace `dr-vm-probe`, apply it, and inspect VMI conditions and events.
It uses the verified ARM64 Fedora container-disk digest and no host networking,
custom operator images or admission overrides. The temporary VMI was deleted
after collecting the failure, to avoid endless retries.

With `spec.domain.cpu.model: cortex-a57`, admission rejected it:

```text
The request is invalid: spec.domain.cpu.model: currently, host-passthrough is the only model supported on Arm64
```

With the CPU model omitted, admission defaulted it to `host-passthrough`.
The VMI scheduled on `dr-primary-m2` but remained `Ready=False` and could not
execute. Its warning event was:

```text
server error. command SyncVMI failed: "LibvirtError(Code=67, Domain=10, Message='unsupported configuration: CPU mode 'host-passthrough' for aarch64 qemu domain on aarch64 host is not supported by hypervisor')"
```

Thus the stock ARM64 API requires a CPU mode that libvirt cannot use with TCG.
The lab will not bypass validation, mutate generated domains or replace vendor
components to hide this conflict. A halted VM can still exercise object/disk
protection, but it cannot satisfy running-VM failover acceptance. Suitable KVM
hardware (or an explicit change to acceptance) is required unless a supported
execution path is established independently.

## Resuming the remaining acceptance work

Do not rebuild an Altra host hoping that additional masters or memory will
resolve this execution failure. The current work has moved to a separate
x86_64 host with nested KVM; that environment still needs independent workload
execution and recovery evidence.

A candidate environment must first demonstrate usable KVM in the OpenShift
nodes, not merely advertise ARM64 or accept the emulation setting. Options are
bare-metal nodes or a host/CPU/kernel combination that actually exposes nested
virtualization to the node guests. A different architecture requires matching
OpenShift artifacts, manifests and workload images; this repository's ARM64 pins
must not simply be reused. These are prerequisites, not a support certification.

On an agreed target, the outstanding acceptance sequence is:

1. Verify node KVM exposure and run the minimal stock VM through normal admission;
   observe the VMI Running and Ready, not just scheduled or an available HCO.
2. Protect a PVC-backed test VM using the installed DR policy and observe current
   disk and object-protection checkpoints before inducing a site outage.
3. Establish real source isolation/fencing before requesting unplanned failover;
   never synthesize fencing status or permit simultaneous source/target writers.
4. Observe the recovered VMI Running and Ready on recovery, verify its disk data,
   and record the operation and cleanup results separately from infrastructure.

No VM execution or failover pass is recorded yet. The stopped-VM diagnostic and
its unresolved source-PVC cleanup are not substitutes for this sequence.

## Hardware references

- [Ampere nested virtualization discussion](https://community.amperecomputing.com/t/issues-with-openstack-instance-creation-and-nested-virtualization-on-arm-host-with-qemu/1050)
- [RHEL 9 nested virtualization requirements](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_and_managing_virtualization/creating-nested-virtual-machines_configuring-and-managing-virtualization)

If shipped emulation cannot execute the workload, hardware with nested KVM or
bare-metal OpenShift nodes remains necessary. A PVC-backed container test can
validate storage recovery but cannot substitute for the requested VM failover.
