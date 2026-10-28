# DR lab plan and acceptance status

This replaces the original implementation sketch. Inventory and playbooks are
now implemented; historical sketches in Git history are not current instructions.

## Implemented topology

- `dr-hub`: ACM hub SNO, bootstrap-in-place, 12 vCPU / 40 GiB / 160 GiB root.
- `dr-primary` and `dr-recovery`: three schedulable masters each, real UPI
  installation with temporary bootstrap guests and ownership-guarded removal.
- Each master: 20 vCPU / 40 GiB / 120 GiB root + dedicated 120 GiB ODF disk.
- Two temporary bootstraps: 4 vCPU / 16 GiB / 60 GiB each.
- Steady budget: 132 vCPU, 280 GiB RAM, 1,600 GiB virtual root/data capacity.
  Bootstrap peak: 140 vCPU, 312 GiB RAM, 1,720 GiB virtual capacity, plus host
  headroom. Thin allocation is not a substitute for capacity planning.
- Default network: `192.168.126.0/24`; hub `.11`, primary VIP `.12` and masters
  `.13`–`.15`, recovery VIP `.16` and masters `.17`–`.19`, bootstraps `.21`/`.22`.
  Actual settings live in `inventory/group_vars/all/`.

## Completed infrastructure acceptance

- [x] Pinned OpenShift 4.22.16 ARM64 artifacts, fresh ignition and time relay.
- [x] Core install, exact Ready membership, schedulable masters, safe bootstrap cleanup.
- [x] Virtualization operator gates, full ACM hub, managed-cluster add-ons.
- [x] Standard replicated three-node ODF, RBD and object provisioning.
- [x] Submariner and real cross-site HTTP/authenticated TLS S3 exchange.
- [x] GitOps/OADP prerequisites and supported CA configuration.
- [x] Managed regional-DR policy, peering, mirroring and operator rollout gates.
- [x] Full teardown + single untagged infrastructure deployment, without manual
  recovery/retry: 2026-10-28, 756 ok / 220 changed / 0 failed / 0 rescued / 0 ignored.
- [x] Final core-state and seven-guest clock verification; private evidence retained.

See [rebuild validation](docs/rebuild-validation.md) for evidence and limitations.
This is a test-only deployment, not certification of a supported production DR
architecture or independent physical failure domains.

## Remaining mandatory acceptance

- [ ] Execute a minimal stock PVC-backed VM, observe Running and Ready.
- [ ] Protect its disk/object state and perform actual unplanned failover with
  real source isolation/fencing, then verify recovery execution and disk data.

These remain blocked by the tested host's nested ARM virtualization limitations
and the stock ARM64 admission/TCG CPU-mode conflict. Preserve the healthy lab
pending compatible hardware; do not redeploy or bypass validation to hide the
blocker. The separate halted-VM diagnostic is not a substitute and retains a
historical unresolved source-PVC cleanup failure.

See [hardware blocker and handoff](docs/hardware-blocker.md) for the remaining
sequence. No full mission completion is claimed.
