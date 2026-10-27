# dr-lab

Three single-node OpenShift (SNO) clusters on one libvirt host — the
foundation of a disaster-recovery lab: an ACM **hub**, a **primary**, and
a **recovery** cluster, each its own cluster domain, pod/service CIDRs,
and bootstrap-in-place (BiP) install. Targets the Fedora aarch64
(Ampere) lab host with distribution QEMU + edk2 firmware.

Ported from [cxl-lab](https://github.com/shanemcd/cxl-lab) conventions:
numbered playbook pipeline, taxonomy-driven group_vars, checksum-pinned
GA artifacts, fresh-window ignition gating, and reverse-layer teardown.

## Topology

| Node     | Role    | Cluster domain       | IP (default net 192.168.126.0/24) |
| -------- | ------- | -------------------- | --------------------------------- |
| `hub`    | SNO/ACM | `hub.ocp.lab`        | 192.168.126.10                    |
| `primary`| SNO     | `primary.ocp.lab`    | 192.168.126.11                    |
| `recovery`| SNO    | `recovery.ocp.lab`   | 192.168.126.12                    |

- OpenShift **4.22 GA** (pinned `ocp_version` in
  `inventory/group_vars/all/versions.yml`), aarch64 mirror + RHCOS
  `rhel-9` stream ISO, checksums cross-checked on every run.
- Per cluster: api/api-int + concrete route + wildcard `*.apps` DNS
  records (libvirt dnsmasq + host `/etc/hosts`), unique pod/service
  CIDRs (see `topology.yml`).
- Each SNO: BiP install (live ISO + blank virtio target + fw_cfg
  ignition), one persistent libvirt domain, autostart with the lab
  network.

## Usage

```bash
# One-time: collections + a pull secret at ~/pull-secret.txt
ansible-galaxy collection install -p . -r requirements.yml

# Full pipeline (host prep → artifacts → network → ignition → VMs →
# cluster install → verify)
ansible-playbook shanemcd.dr_lab.site

# Or stage by stage
ansible-playbook shanemcd.dr_lab.01_host_prep
ansible-playbook shanemcd.dr_lab.02_artifacts
ansible-playbook shanemcd.dr_lab.03_network
ansible-playbook shanemcd.dr_lab.04_ignition
ansible-playbook shanemcd.dr_lab.05_snos
ansible-playbook shanemcd.dr_lab.06_install

# Checks + evidence report
ansible-playbook shanemcd.dr_lab.verify

# Reverse-layer teardown (all, or --tags vms|network|artifacts|install-data)
ansible-playbook shanemcd.dr_lab.teardown
```

Consoles: `https://console-openshift-console.apps.<node>.ocp.lab`
(kubeconfigs under `~/ocp-install-dr/<node>/auth/`).

## Layout

- `inventory/group_vars/all/` — taxonomy: `host`, `network`, `paths`,
  `topology`, `versions`, `secrets`.
- `ansible_collections/shanemcd/dr_lab/roles/` — `workspace`, `host_prep`,
  `artifacts`, `network`, `install_config`, `vms`, `cluster_install`,
  `teardown`, `verify`.
- Idempotent, check-mode-friendly; teardown reverses exactly the host
  changes the pipeline makes.

## Notes

- Ignition is generated at most once per 12 h window (MCS certificate
  validity); a stale/partial state fails with teardown guidance.
- The libvirt network refuses teardown while guest ports are attached —
  tear down the `vms` layer first.
- DR content (ACM, Ceph, RamenDR) comes in later phases; this repo is
  phase 1: three converged SNOs.
