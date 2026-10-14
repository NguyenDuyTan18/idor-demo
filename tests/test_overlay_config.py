import base64
import configparser
import ipaddress
import unittest
from pathlib import Path
import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parents[1]


class OverlayConfigTests(unittest.TestCase):
    def test_rendered_wireguard_routes_cover_four_distinct_endpoints(self):
        inventory = yaml.safe_load((ROOT / 'interconnect/inventory.example.yml').read_text(encoding='utf-8'))['all']
        peers = inventory['children']['lab_peers']['hosts']
        hub = inventory['children']['lab_hub']['hosts']
        hostvars = peers | hub
        for index, value in enumerate(hostvars.values(), 1):
            public = base64.b64encode(bytes([index]) * 32).decode()
            value['idor_wg_public'] = {'stdout': public}
            value['idor_wg_private'] = {'content': base64.b64encode(public.encode()).decode()}
        env = Environment(loader=FileSystemLoader(ROOT / 'interconnect/templates'), undefined=StrictUndefined)
        env.filters['b64decode'] = lambda value: base64.b64decode(value).decode()
        common = inventory['vars'] | {'groups': {'lab_hub': list(hub), 'lab_peers': list(peers)}, 'hostvars': hostvars}
        rendered_hub = env.get_template('hub.conf.j2').render(common | hub['lab-hub'])
        # Repeated [Peer] sections are valid WireGuard syntax. Read peer blocks separately.
        blocks = rendered_hub.split('[Peer]')[1:]
        self.assertEqual(len(blocks), 4)
        routes = []
        public_keys = []
        for block in blocks:
            parsed = configparser.ConfigParser()
            parsed.read_string('[Peer]' + block)
            routes.append(ipaddress.ip_network(parsed['Peer']['AllowedIPs']))
            public_keys.append(parsed['Peer']['PublicKey'])
        self.assertEqual(len(set(public_keys)), 4)
        self.assertTrue(all(route.prefixlen == 32 for route in routes))
        for name, variables in peers.items():
            config = env.get_template('peer.conf.j2').render(common | variables)
            parsed = configparser.ConfigParser()
            parsed.read_string(config)
            self.assertEqual(len(base64.b64decode(parsed['Interface']['PrivateKey'])), 32)
            self.assertEqual(parsed['Interface']['Address'], variables['idor_overlay_ip'] + '/32')
            self.assertEqual(parsed['Peer']['PersistentKeepalive'], '25')
            allowed = ipaddress.ip_network(parsed['Peer']['AllowedIPs'])
            for other in peers.values():
                self.assertIn(ipaddress.ip_address(other['idor_overlay_ip']), allowed)
                self.assertTrue(any(ipaddress.ip_address(other['idor_overlay_ip']) in route for route in routes))
            # No duplicate private subnet is announced to the hub.
            for excluded in ['10.30.20.5', '10.30.30.5', '192.168.128.5', '8.8.8.8']:
                self.assertNotIn(ipaddress.ip_address(excluded), allowed)


if __name__ == '__main__':
    unittest.main()
