import importlib.util
import unittest
import json
import tempfile
from types import SimpleNamespace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BattleNICTests(unittest.TestCase):
    def setUp(self):
        source = ROOT / 'battle-network/guest/configure_nic.py'
        self.assertTrue(source.is_file(), 'Shared-network guest configuration is required')
        spec = importlib.util.spec_from_file_location('battle_nic', source)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def test_valid_configs_have_unique_battle_addresses(self):
        for ip in ['10.90.0.11', '10.90.0.12', '10.90.0.21', '10.90.0.22']:
            mac, address = self.module.validate_config({'mac_address': 'fa:16:3e:12:34:56', 'ip_address': ip})
            self.assertEqual(mac, 'fa:16:3e:12:34:56')
            self.assertEqual(address, ip + '/24')

    def test_invalid_or_management_addresses_are_rejected(self):
        cases = [
            {'mac_address': 'bad', 'ip_address': '10.90.0.11'},
            {'mac_address': 'ff:ff:ff:ff:ff:ff', 'ip_address': '10.90.0.11'},
            {'mac_address': '00:00:00:00:00:00', 'ip_address': '10.90.0.11'},
            {'mac_address': 'fa:16:3e:12:34:56', 'ip_address': '192.168.128.2'},
            {'mac_address': 'fa:16:3e:12:34:56', 'ip_address': '10.90.0.11; reboot'},
        ]
        for case in cases:
            with self.assertRaises(ValueError):
                self.module.validate_config(case)

    def test_networkmanager_only_changes_matched_nic_and_never_default_route(self):
        commands = self.module.nm_commands('ens9', 'fa:16:3e:12:34:56', '10.90.0.11/24', None)
        flat = [part for command in commands for part in command]
        self.assertIn('ipv4.never-default', flat)
        self.assertIn('ipv6.method', flat)
        self.assertNotIn('restart', flat)
        self.assertNotIn('ens3', flat)
        self.assertEqual(commands[-1], ['nmcli', 'connection', 'up', 'idor-battle', 'ifname', 'ens9'])
        update = next(command for command in commands if 'modify' in command)
        self.assertEqual(update[update.index('ipv4.gateway') + 1], '')
        self.assertEqual(update[update.index('ipv4.dns') + 1], '')

    def test_foreign_networkmanager_profile_is_not_overwritten(self):
        with self.assertRaises(ValueError):
            self.module.nm_commands('ens9', 'fa:16:3e:12:34:56', '10.90.0.11/24', 'fa:16:3e:00:00:01')

    def test_networkd_config_has_mac_match_without_gateway_or_dns(self):
        config = self.module.networkd_config('fa:16:3e:12:34:56', '10.90.0.12/24')
        self.assertIn('MACAddress=fa:16:3e:12:34:56', config)
        self.assertIn('Address=10.90.0.12/24', config)
        self.assertIn('DHCP=no', config)
        self.assertNotIn('Gateway=', config)
        self.assertNotIn('DNS=', config)

    def test_conflicting_management_route_is_rejected(self):
        normal = [{'dst': 'default', 'dev': 'ens3'}, {'dst': '10.80.0.0/24', 'dev': 'ens4'}]
        self.module.validate_routes(normal, 'ens9')
        self.module.validate_routes(normal + [{'dst': '10.90.0.0/24', 'dev': 'ens9'}], 'ens9')
        with self.assertRaises(ValueError):
            self.module.validate_routes(normal + [{'dst': '10.90.0.0/24', 'dev': 'ens3'}], 'ens9')

    def scenario(self, manager='none', wrong_address=False, changed_default=False, missing_mac=False):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        iface = root / 'net/ens9'
        iface.mkdir(parents=True)
        mac = 'fa:16:3e:12:34:56'
        (iface / 'address').write_text('fa:16:3e:00:00:01' if missing_mac else mac)
        calls = []
        default_reads = 0
        def runner(argv, check=True):
            nonlocal default_reads
            calls.append(argv)
            code, stdout = 0, ''
            if argv[:3] == ['systemctl', 'is-active', 'NetworkManager']:
                code = 0 if manager == 'nm' else 3
            elif argv[:3] == ['systemctl', 'is-active', 'systemd-networkd']:
                code = 0 if manager == 'networkd' else 3
            elif argv[:2] == ['nmcli', '-g']:
                code = 10
            elif argv[:4] == ['ip', '-j', '-4', 'route']:
                if argv[-1] == 'default':
                    default_reads += 1
                    gateway = '192.168.1.2' if changed_default and default_reads > 1 else '192.168.1.1'
                    stdout = json.dumps([{'dst': 'default', 'dev': 'ens3', 'gateway': gateway}])
                else:
                    stdout = json.dumps([{'dst': '10.80.0.0/24', 'dev': 'ens4'}])
            elif argv[:4] == ['ip', '-j', '-4', 'address']:
                stdout = json.dumps([{'addr_info': [{'local': '10.90.0.99' if wrong_address else '10.90.0.11', 'prefixlen': 24}]}])
            return SimpleNamespace(returncode=code, stdout=stdout)
        return root, calls, runner, {'mac_address': mac, 'ip_address': '10.90.0.11'}

    def test_configure_all_supported_guest_managers_preserves_default_routes(self):
        for manager, expected in [('nm', 'NetworkManager'), ('networkd', 'systemd-networkd'), ('none', 'boot-oneshot')]:
            root, calls, runner, config = self.scenario(manager)
            result = self.module.configure(config, runner, root / 'net', root / 'networkd/battle.network')
            self.assertEqual(result['interface'], 'ens9')
            self.assertEqual(result['manager'], expected)
            self.assertFalse(any('restart' in argv for argv in calls))
            self.assertFalse(any('ens3' in argv or 'ens4' in argv for argv in calls))

    def test_missing_mac_default_route_change_and_failed_address_stop_configuration(self):
        for kwargs in [{'missing_mac': True}, {'changed_default': True}, {'wrong_address': True}]:
            root, calls, runner, config = self.scenario(**kwargs)
            with self.assertRaises(ValueError):
                self.module.configure(config, runner, root / 'net', root / 'networkd/battle.network')

    def test_foreign_networkd_file_is_not_replaced(self):
        root, calls, runner, config = self.scenario('networkd')
        file = root / 'foreign.network'
        original = '[Match]\nMACAddress=fa:16:3e:00:00:01\n'
        file.write_text(original)
        with self.assertRaises(ValueError):
            self.module.configure(config, runner, root / 'net', file)
        self.assertEqual(file.read_text(), original)


if __name__ == '__main__':
    unittest.main()
