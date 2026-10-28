"""Default inventory consistency, not validation of arbitrary user overrides."""
from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
VARS = ROOT / "inventory/group_vars/all"


def load(name):
    return yaml.safe_load((VARS / f"{name}.yml").read_text())


class InventoryContractTests(unittest.TestCase):
    def test_default_site_selectors_agree(self):
        topology = load("topology")
        clusters = topology["clusters"]
        names = [c["name"] for c in clusters]
        self.assertEqual(len(names), len(set(names)))
        acm = load("acm")
        self.assertEqual(acm["acm_cluster"], next(c["name"] for c in clusters if c["role"] == "hub"))
        sites = [next(c["name"] for c in clusters if c["role"] == role)
                 for role in ("primary", "recovery")]
        self.assertEqual(acm["acm_spokes"], sites)
        self.assertEqual(load("storage")["storage_clusters"], sites)
        self.assertEqual(load("virtualization")["virtualization_clusters"], sites)
        self.assertEqual(load("workload")["workload_storage_class"],
                         load("storage")["storage_rbd_storageclass"])

    def test_default_ipv4_suffixes_are_usable_distinct_and_reserved(self):
        network = load("network")
        self.assertEqual(network["lab_subnet_netmask"], "255.255.255.0")
        octets = network["lab_subnet_prefix"].split(".")
        self.assertEqual(len(octets), 3)
        self.assertTrue(all(o.isdecimal() and 0 <= int(o) <= 255 for o in octets))
        claimed = [network["host_gateway_suffix"], network["network_probe_suffix"]]
        for cluster in load("topology")["clusters"]:
            if cluster["install_flavor"] == "sno":
                claimed.append(cluster["ip_suffix"])
            else:
                claimed.extend([cluster["api_vip_suffix"], cluster["bootstrap_ip_suffix"]])
                claimed.extend(m["ip_suffix"] for m in cluster["masters"])
        self.assertEqual(len(claimed), len(set(claimed)))
        self.assertTrue(all(1 <= n <= 254 for n in claimed))
        start, end = (network[f"network_dhcp_range_{key}_suffix"] for key in ("start", "end"))
        self.assertTrue(1 <= start <= end <= 254)
        self.assertFalse(set(claimed) & set(range(start, end + 1)))


if __name__ == "__main__":
    unittest.main()
