output "battle_network_id" {
  value = openstack_networking_network_v2.battle.id
}

output "selected_vm_names" {
  description = "Review these real Nova VM names against the trainee/run/sandbox assignment before applying."
  value       = module.existing_vms.vm_names
}

output "battle_ports" {
  description = "Public network metadata consumed by configure-guests.yml. No credentials or private keys."
  value = {
    for key, endpoint in local.endpoints : key => {
      team         = endpoint.team
      role         = endpoint.role
      server_id    = endpoint.server_id
      sandbox_uuid = var.teams[endpoint.team].sandbox_uuid
      ip_address   = endpoint.ip
      mac_address  = openstack_networking_port_v2.battle[key].mac_address
      port_id      = openstack_compute_interface_attach_v2.battle[key].port_id
    }
  }
}
