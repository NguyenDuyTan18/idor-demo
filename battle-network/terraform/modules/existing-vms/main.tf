terraform {
  required_providers {
    openstack = { source = "terraform-provider-openstack/openstack" }
  }
}

variable "endpoints" {
  type = map(object({ team = string, role = string, server_id = string, ip = string }))
}

data "openstack_compute_instance_v2" "vm" {
  for_each = var.endpoints
  id       = each.value.server_id
}

output "roles_valid" {
  value = alltrue([
    for key, endpoint in var.endpoints :
    contains([for nic in data.openstack_compute_instance_v2.vm[key].network : nic.fixed_ip_v4], endpoint.role == "kali" ? "10.80.0.10" : "10.80.0.20")
  ])
}

output "vm_names" {
  value = { for key, vm in data.openstack_compute_instance_v2.vm : key => vm.name }
}
