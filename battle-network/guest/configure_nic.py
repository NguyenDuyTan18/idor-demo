"""Configure only the extra battle NIC identified by its Neutron MAC address."""
import argparse
import ipaddress
import json
import re
import subprocess
from pathlib import Path

ALLOWED_IPS = {'10.90.0.11', '10.90.0.12', '10.90.0.21', '10.90.0.22'}
BATTLE = ipaddress.ip_network('10.90.0.0/24')


def validate_config(config):
    mac = str(config.get('mac_address', '')).lower()
    ip = str(config.get('ip_address', ''))
    if not re.fullmatch(r'(?:[0-9a-f]{2}:){5}[0-9a-f]{2}', mac):
        raise ValueError('Invalid Neutron MAC address')
    if mac == '00:00:00:00:00:00' or int(mac[:2], 16) & 1:
        raise ValueError('MAC must identify a unicast interface')
    if ip not in ALLOWED_IPS:
        raise ValueError('Only the four assigned battle addresses are allowed')
    return mac, ip + '/24'


def validate_routes(routes, iface):
    for route in routes:
        dst = route.get('dst', 'default')
        if dst == 'default' or route.get('dev') == iface:
            continue
        net = ipaddress.ip_network(dst, strict=False)
        if net.version == 4 and net.prefixlen and net.overlaps(BATTLE):
            raise ValueError('Battle subnet overlaps an existing route on another interface')


def nm_commands(iface, mac, address, existing_mac):
    if existing_mac is not None and existing_mac.lower() != mac:
        raise ValueError('Existing idor-battle profile belongs to another NIC')
    commands = []
    if existing_mac is None:
        commands.append(['nmcli', 'connection', 'add', 'type', 'ethernet', 'con-name',
                         'idor-battle', 'ifname', iface, '802-3-ethernet.mac-address', mac,
                         'ipv4.method', 'manual', 'ipv4.addresses', address,
                         'ipv4.never-default', 'yes', 'ipv6.method', 'disabled'])
    commands.append(['nmcli', 'connection', 'modify', 'idor-battle',
                     'connection.interface-name', '', '802-3-ethernet.mac-address', mac,
                     'connection.autoconnect', 'yes', 'ipv4.method', 'manual',
                     'ipv4.addresses', address, 'ipv4.gateway', '', 'ipv4.dns', '',
                     'ipv4.ignore-auto-dns', 'yes', 'ipv4.never-default', 'yes',
                     'ipv6.method', 'disabled'])
    commands.append(['nmcli', 'connection', 'up', 'idor-battle', 'ifname', iface])
    return commands


def networkd_config(mac, address):
    return (f'[Match]\nMACAddress={mac}\n\n[Network]\nAddress={address}\n'
            'DHCP=no\nIPv6AcceptRA=no\nLinkLocalAddressing=no\n')


def command(argv, check=True):
    return subprocess.run(argv, check=check, capture_output=True, text=True, timeout=45)


def configure(config, runner=command, interfaces_root=Path('/sys/class/net'),
              networkd_path=Path('/etc/systemd/network/00-idor-battle.network')):
    mac, address = validate_config(config)
    interfaces = [entry.name for entry in interfaces_root.iterdir()
                  if (entry / 'address').is_file() and (entry / 'address').read_text().strip().lower() == mac]
    if len(interfaces) != 1:
        raise ValueError('The attached Neutron MAC must match exactly one local NIC')
    iface = interfaces[0]
    before = json.loads(runner(['ip', '-j', '-4', 'route', 'show', 'default']).stdout)
    routes = json.loads(runner(['ip', '-j', '-4', 'route', 'show', 'table', 'all']).stdout)
    validate_routes(routes, iface)
    if runner(['systemctl', 'is-active', 'NetworkManager'], check=False).returncode == 0:
        profile = runner(['nmcli', '-g', '802-3-ethernet.mac-address', 'connection', 'show', 'idor-battle'], check=False)
        if profile.returncode not in (0, 10):
            raise ValueError('Cannot inspect the NetworkManager battle profile')
        existing_mac = profile.stdout.strip() if profile.returncode == 0 else None
        for argv in nm_commands(iface, mac, address, existing_mac):
            runner(argv)
        manager = 'NetworkManager'
    elif runner(['systemctl', 'is-active', 'systemd-networkd'], check=False).returncode == 0:
        if networkd_path.exists() and f'MACAddress={mac}' not in networkd_path.read_text():
            raise ValueError('Existing battle networkd file belongs to another NIC')
        networkd_path.parent.mkdir(parents=True, exist_ok=True)
        networkd_path.write_text(networkd_config(mac, address))
        runner(['networkctl', 'reload'])
        runner(['networkctl', 'reconfigure', iface])
        manager = 'systemd-networkd'
    else:
        # The dedicated oneshot service repeats this at boot. No other NIC is restarted.
        runner(['ip', 'link', 'set', 'dev', iface, 'up'])
        runner(['ip', 'address', 'replace', address, 'dev', iface])
        manager = 'boot-oneshot'
    after = json.loads(runner(['ip', '-j', '-4', 'route', 'show', 'default']).stdout)
    canonical = lambda rows: sorted(json.dumps(row, sort_keys=True) for row in rows)
    if canonical(before) != canonical(after):
        raise ValueError('Default routes changed; stop and inspect the guest networking')
    observed = json.loads(runner(['ip', '-j', '-4', 'address', 'show', 'dev', iface]).stdout)
    if not any(info.get('local') == config['ip_address'] and info.get('prefixlen') == 24
               for link in observed for info in link.get('addr_info', [])):
        raise ValueError('The battle address was not configured successfully')
    return {'interface': iface, 'ip_address': config['ip_address'], 'manager': manager}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    args = parser.parse_args()
    print(json.dumps(configure(json.loads(Path(args.config).read_text()))))


if __name__ == '__main__':
    main()
