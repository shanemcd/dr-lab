# dr-lab

Ansible automation for a **three-SNO disaster-recovery lab** on one libvirt
host: `hub` (future ACM hub), `primary`, and `recovery` single-node OpenShift
clusters — each with its own cluster domain, pod/service CIDRs, and
bootstrap-in-place install. Built from a bare Fedora aarch64 server with
nothing but SSH (libvirt, QEMU, and the rest of the host package set are
ensured by the pipeline itself).

All content lives in the [`shanemcd.dr_lab`](ansible_collections/shanemcd/dr_lab)
collection — see its [README](ansible_collections/shanemcd/dr_lab/README.md)
for the topology, usage, and layout. Phase 1 (three converged SNOs) is complete; DR content is layered on top:
OpenShift Virtualization and ACM (multicluster-engine hub with both spokes
imported) are live. Ceph and RamenDR come next.
