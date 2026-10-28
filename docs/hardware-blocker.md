# VM DR validation is blocked on this host

The proposed compact-cluster rebuild has **not** been deployed. The existing
three SNOs are still intact. Offline tests passing is not evidence of live
cluster installation or DR working.

## Observed hardware and probes

The physical host is an Ampere Altra Q80-30 / Neoverse-N1, aarch64.
OpenShift nodes are libvirt/KVM guests on that host. A KubeVirt test VM would
therefore require a second, nested virtualization level.

Read-only SSH probe of existing `dr-primary` (192.168.126.12):

```text
uname -m: aarch64
/dev/kvm: absent (NO_GUEST_KVM)
CPU implementer: 0x41
CPU part: 0xd0c
```

A diskless, paused QEMU capability probe on the physical host:

```sh
timeout 5 qemu-system-aarch64 -accel kvm -machine virt,virtualization=on \
  -cpu host -m 128 -nodefaults -display none -S
```

Exited immediately with code 1:

```text
qemu-system-aarch64: mach-virt: host kernel KVM does not support providing Virtualization extensions to the guest CPU
```

Adding masters or RAM cannot fix this CPU limitation. Installing the
virtualization operator alone would not demonstrate that a VM can execute.
Software emulation would change the no-hacks requirement and is not an
implicitly authorized substitute.

## Sources consulted

- Ampere community explanation of Altra/Altra Max lacking nested virtualization:
  https://community.amperecomputing.com/t/issues-with-openstack-instance-creation-and-nested-virtualization-on-arm-host-with-qemu/1050
- Red Hat's RHEL 9 nested virtualization requirements and limitations (the
  existing OpenShift guests report RHCOS 9.8 / kernel 5.14):
  https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_and_managing_virtualization/creating-nested-virtual-machines_configuring-and-managing-virtualization

ARM64 OpenShift Virtualization support must not be confused with support for
nesting on this particular processor. The local QEMU failure independently
confirms that this host cannot expose the required virtualization extensions.

## Decision needed before destructive rebuild

Choose either:

1. Move the VM DR lab to hardware with working nested KVM, or use suitable
   bare-metal OpenShift nodes. Access and capability checks are needed before
   committing to that design.
2. Keep this host and explicitly change the validation workload to a
   PVC-backed container application. This can exercise storage/application DR,
   but **does not satisfy the requested VM failover test**. ODF/DR architecture
   and version support still need independent verification.

Until that choice is made, do not tear down the current lab or claim completion
of the one-shot rebuild or VM failover objective.
