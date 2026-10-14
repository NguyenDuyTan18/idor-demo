locals {
  battle_cidr = "10.90.0.0/24"
  endpoints = {
    team-a-kali = { team = "A", role = "kali", server_id = var.teams["A"].kali_server_id, ip = "10.90.0.11" }
    team-a-web  = { team = "A", role = "web", server_id = var.teams["A"].web_server_id, ip = "10.90.0.12" }
    team-b-kali = { team = "B", role = "kali", server_id = var.teams["B"].kali_server_id, ip = "10.90.0.21" }
    team-b-web  = { team = "B", role = "web", server_id = var.teams["B"].web_server_id, ip = "10.90.0.22" }
  }
}

# Read existing VMs. This configuration creates no VM and no hub.
module "existing_vms" {
  source    = "./modules/existing-vms"
  endpoints = local.endpoints
}

resource "openstack_networking_network_v2" "battle" {
  name                  = "idor-battle-pool-${var.pool_id}"
  admin_state_up        = true
  shared                = false
  port_security_enabled = true
  lifecycle {
    precondition {
      condition     = module.existing_vms.roles_valid
      error_message = "A selected VM does not have the expected original Kali/web IP. Inspect the trainee/sandbox/VM mapping before applying."
    }
  }
}

resource "openstack_networking_subnet_v2" "battle" {
  name        = "idor-battle-pool-${var.pool_id}"
  network_id  = openstack_networking_network_v2.battle.id
  cidr        = local.battle_cidr
  ip_version  = 4
  enable_dhcp = false
  no_gateway  = true
}

resource "openstack_networking_secgroup_v2" "battle" {
  name                 = "idor-battle-pool-${var.pool_id}"
  description          = "IDOR exercise ports only; original management interfaces keep their existing policies."
  delete_default_rules = true
}

resource "openstack_networking_secgroup_rule_v2" "battle" {
  for_each = {
    http_in  = { direction = "ingress", protocol = "tcp", min = 8080, max = 8080 }
    http_out = { direction = "egress", protocol = "tcp", min = 8080, max = 8080 }
    ping_in  = { direction = "ingress", protocol = "icmp", min = null, max = null }
    ping_out = { direction = "egress", protocol = "icmp", min = null, max = null }
  }
  security_group_id = openstack_networking_secgroup_v2.battle.id
  direction         = each.value.direction
  ethertype         = "IPv4"
  protocol          = each.value.protocol
  port_range_min    = each.value.min
  port_range_max    = each.value.max
  remote_ip_prefix  = local.battle_cidr
}

resource "openstack_networking_port_v2" "battle" {
  for_each              = local.endpoints
  name                  = "idor-pool-${var.pool_id}-${each.key}"
  network_id            = openstack_networking_network_v2.battle.id
  admin_state_up        = true
  port_security_enabled = true
  security_group_ids    = [openstack_networking_secgroup_v2.battle.id]
  fixed_ip {
    subnet_id  = openstack_networking_subnet_v2.battle.id
    ip_address = each.value.ip
  }
}

resource "openstack_compute_interface_attach_v2" "battle" {
  for_each    = local.endpoints
  instance_id = each.value.server_id
  port_id     = openstack_networking_port_v2.battle[each.key].id
}
