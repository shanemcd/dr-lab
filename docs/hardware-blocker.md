# VM execution capabilities and validation limits

## Current state

The real compact-cluster rebuild is live: one ACM hub and two three-master
OpenShift 4.22.16 ARM64 clusters. Both sites passed standard ODF provisioning,
Submariner application traffic, authenticated remote S3 with verified TLS,
and current ODF Regional-DR peering/policy gates. These do **not** establish
successful VM execution, protected VM recovery, or full one-shot redeployment.

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

The user authorized proceeding through the cluster/storage/DR layers first and
considering emulation afterward. Those infrastructure gates now pass. The
inventory explicitly selects `virtualization_use_emulation: true`; the reusable
role defaults to false. It feeds `KVM_EMULATION` through the OLM Subscription's
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

## Hardware references

- [Ampere nested virtualization discussion](https://community.amperecomputing.com/t/issues-with-openstack-instance-creation-and-nested-virtualization-on-arm-host-with-qemu/1050)
- [RHEL 9 nested virtualization requirements](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_and_managing_virtualization/creating-nested-virtual-machines_configuring-and-managing-virtualization)

If shipped emulation cannot execute the workload, hardware with nested KVM or
bare-metal OpenShift nodes remains necessary. A PVC-backed container test can
validate storage recovery but cannot substitute for the requested VM failover.
