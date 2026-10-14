mock_provider "openstack" {}

# The read-only discovery module is overridden; no real Nova lookup is run.
# Runtime discovery is validated by schema and must be exercised on the real cloud.
override_module {
  target  = module.existing_vms
  outputs = { roles_valid = true, vm_names = { team-a-kali = "fixture-a-kali", team-a-web = "fixture-a-web", team-b-kali = "fixture-b-kali", team-b-web = "fixture-b-web" } }
}

variables {
  pool_id = 7
  teams = {
    A = { sandbox_uuid = "00000000-0000-4000-8000-000000000001", kali_server_id = "10000000-0000-4000-8000-000000000001", web_server_id = "20000000-0000-4000-8000-000000000002" }
    B = { sandbox_uuid = "00000000-0000-4000-8000-000000000002", kali_server_id = "30000000-0000-4000-8000-000000000003", web_server_id = "40000000-0000-4000-8000-000000000004" }
  }
}

run "shared_network_without_hub" {
  command = plan
  assert {
    condition     = length(openstack_networking_port_v2.battle) == 4 && length(openstack_compute_interface_attach_v2.battle) == 4
    error_message = "Four existing VM endpoints must get one additional port each."
  }
  assert {
    condition     = !openstack_networking_subnet_v2.battle.enable_dhcp && openstack_networking_subnet_v2.battle.no_gateway
    error_message = "The additional network must not inject DHCP, a default gateway, or DNS."
  }
  assert {
    condition     = output.battle_ports["team-a-kali"].ip_address == "10.90.0.11" && output.battle_ports["team-b-web"].ip_address == "10.90.0.22"
    error_message = "Team endpoint addresses must match the trainee guide."
  }
  assert {
    condition     = length(openstack_networking_secgroup_rule_v2.battle) == 4 && openstack_networking_secgroup_rule_v2.battle["http_in"].port_range_min == 8080
    error_message = "Only the lab HTTP and ICMP rules are expected."
  }
}

run "reject_placeholder_ids" {
  command = plan
  variables {
    teams = {
      A = { sandbox_uuid = "REPLACE", kali_server_id = "10000000-0000-4000-8000-000000000001", web_server_id = "20000000-0000-4000-8000-000000000002" }
      B = { sandbox_uuid = "00000000-0000-4000-8000-000000000002", kali_server_id = "30000000-0000-4000-8000-000000000003", web_server_id = "40000000-0000-4000-8000-000000000004" }
    }
  }
  expect_failures = [var.teams]
}

run "reject_duplicate_vms" {
  command = plan
  variables {
    teams = {
      A = { sandbox_uuid = "00000000-0000-4000-8000-000000000001", kali_server_id = "10000000-0000-4000-8000-000000000001", web_server_id = "10000000-0000-4000-8000-000000000001" }
      B = { sandbox_uuid = "00000000-0000-4000-8000-000000000002", kali_server_id = "30000000-0000-4000-8000-000000000003", web_server_id = "40000000-0000-4000-8000-000000000004" }
    }
  }
  expect_failures = [var.teams]
}

run "reject_wrong_vm_role" {
  command = plan
  override_module {
    target  = module.existing_vms
    outputs = { roles_valid = false, vm_names = {} }
  }
  expect_failures = [openstack_networking_network_v2.battle]
}

run "reject_invalid_pool" {
  command = plan
  variables { pool_id = 0 }
  expect_failures = [var.pool_id]
}
