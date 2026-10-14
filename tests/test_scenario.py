import ipaddress
import json
import unittest
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


class ScenarioTests(unittest.TestCase):
    def read(self, path):
        file = ROOT / path
        self.assertTrue(file.is_file(), f'Missing scenario artifact: {path}')
        return yaml.safe_load(file.read_text(encoding='utf-8'))

    def test_each_sandbox_has_two_hosts_and_one_router(self):
        topology = self.read('topology.yml')
        self.assertEqual({h['name'] for h in topology['hosts']}, {'attacker', 'server'})
        self.assertEqual(len(topology['routers']), 1)
        mappings = {m['host']: m for m in topology['net_mappings']}
        self.assertEqual(mappings['attacker']['ip'], '10.30.30.5')
        self.assertEqual(mappings['server']['ip'], '10.30.20.5')
        networks = {n['name']: ipaddress.ip_network(n['cidr']) for n in topology['networks']}
        networks['wan'] = ipaddress.ip_network(topology['wan']['cidr'])
        for i, net in enumerate(networks.values()):
            for other in list(networks.values())[i + 1:]:
                self.assertFalse(net.overlaps(other))
        for m in topology['net_mappings'] + topology['router_mappings']:
            self.assertIn(ipaddress.ip_address(m['ip']), networks[m['network']])
        self.assertEqual({m['network'] for m in topology['router_mappings']}, set(networks) - {'wan'})

    def test_apg_matches_training_and_has_no_shared_fallback(self):
        variables = self.read('variables.yml')
        self.assertEqual(variables['idor_flag']['type'], 'password')
        self.assertGreaterEqual(variables['idor_flag']['length'], 24)
        training = self.read('training-definition.json')
        self.assertTrue(training['variant_sandboxes'])
        levels = [l for l in training['levels'] if l['level_type'] == 'TRAINING_LEVEL']
        self.assertEqual(len(levels), 1)
        self.assertTrue(levels[0]['variant_answers'])
        self.assertEqual(levels[0]['answer_variable_name'], 'idor_flag')
        self.assertIsNone(levels[0]['answer'])
        tasks = (ROOT / 'provisioning/roles/server/tasks/main.yml').read_text(encoding='utf-8')
        self.assertIn('idor_flag is defined', tasks)

    def test_overlay_addresses_are_unique_for_all_four_hosts(self):
        inv = self.read('interconnect/inventory.example.yml')['all']['children']
        peers = inv['lab_peers']['hosts']
        self.assertEqual(len(peers), 4)
        ips = [p['idor_overlay_ip'] for p in peers.values()]
        self.assertEqual(len(set(ips)), 4)
        overlay = ipaddress.ip_network('10.200.0.0/24')
        for ip in ips:
            self.assertIn(ipaddress.ip_address(ip), overlay)
        for p in peers.values():
            self.assertIn('ControlPath=none', p['ansible_ssh_common_args'])
        self.assertEqual({p['ansible_host'] for p in peers.values()}, {'attacker', 'server'})
        self.assertEqual(len(inv['lab_hub']['hosts']), 1)

    def test_overlay_does_not_route_management_or_default_network(self):
        peer = (ROOT / 'interconnect/templates/peer.conf.j2').read_text(encoding='utf-8')
        self.assertIn('AllowedIPs = {{ idor_overlay_cidr }}', peer)
        self.assertNotIn('0.0.0.0/0', peer)
        hub = (ROOT / 'interconnect/templates/hub.conf.j2').read_text(encoding='utf-8')
        self.assertIn('idor_overlay_ip }}/32', hub)
        self.assertIn('--dport 8080', hub)
        self.assertIn('DROP', hub)

    def test_kali_access_does_not_depend_on_late_ssh_password_override(self):
        host_vars = self.read('provisioning/host_vars/attacker.yml')
        self.assertEqual(host_vars['user_access_username'], 'user-access')
        self.assertEqual(host_vars['user_access_shell'], '/bin/bash')
        self.assertFalse(host_vars['user_access_sudo'])
        tasks = (ROOT / 'provisioning/roles/attacker/tasks/main.yml').read_text(encoding='utf-8')
        self.assertIn('00-idor-user-access.conf', tasks)
        self.assertIn('sshd -T', tasks)
        self.assertIn('passwordauthentication yes', tasks)
        self.assertIn('pubkeyauthentication yes', tasks)
        self.assertIn('sshd -t', tasks)
        playbook = self.read('provisioning/playbook.yml')
        attacker = next(p for p in playbook if p['hosts'] == 'attacker')
        self.assertTrue(any((r if isinstance(r, str) else r['role']) == 'user-access' for r in attacker['roles']))


if __name__ == '__main__':
    unittest.main()
