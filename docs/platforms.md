# Host platforms

The lab selects native architecture from the managed host, not the controller.
Cross-architecture QEMU emulation is deliberately rejected. Architecture-aware
configuration is not the same as a completed validation on each platform.

| Host architecture | Libvirt machine | Guest serial console | KubeVirt architecture | Status |
| --- | --- | --- | --- | --- |
| x86_64 | q35 + UEFI | ttyS0 | amd64 | Native deployment and guest execution verified; manually assisted recovery demonstrated (see current evidence) |
| aarch64 | virt + UEFI | ttyAMA0 | arm64 | Historical infrastructure deployment only; running-VM DR unproven |

The host must be Red Hat-family Linux with systemd, libvirt, QEMU/KVM, firmware,
and the packages listed in `inventory/group_vars/all/host.yml` available. Fedora
uses `/usr/bin/qemu-system-<architecture>`; RHEL-family distributions use
`/usr/libexec/qemu-kvm`. Package availability varies by distribution and enabled
repositories. Only the actual tested combinations should be considered validated.
Override `host_packages` and `qemu_binary_path` for a distribution with different
packaging; do not assume an untested derivative works.

## Hardware virtualization

`/dev/kvm` on the host is necessary but insufficient: the OpenShift nodes are
virtual machines and must themselves expose KVM to OpenShift Virtualization.
On x86, preflight requires enabled `kvm_intel` or `kvm_amd` nesting. ARM requires
nested virtualization support throughout CPU, firmware, kernel and QEMU. Ampere
Altra lacking that capability cannot meet the running-VM acceptance criteria.
Software emulation is disabled by default and is not a supported substitute.
The final check is a running guest on each managed cluster, not a sysfs flag.

## Release inputs

`inventory/group_vars/all/architecture.yml` defines machine, console, firmware
packages and KubeVirt names. `versions.yml` defines release-specific SHA-256 pins
for client tools and the RHCOS ISO on both architectures. Existing ARM pins are
retained; x86_64 pins were checked against the 4.22.16 mirror manifest and the
checksum-verified installer's `coreos print-stream-json --stream rhel-9` output.
The artifacts role cross-checks pins before use and keys extraction stamps by
both version and architecture. Changing releases requires updating the pins and
ISO build deliberately; never remove checksum validation to accommodate a change.

See [validation](validation.md) for the acceptance criteria. This single-host
lab is for experimentation, not production availability or host-failure DR.
