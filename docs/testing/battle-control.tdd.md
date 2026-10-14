# Battle control TDD evidence

## User journey

As an instructor, I want to provide the two allocated sandbox mappings once, review a Terraform plan, and deploy the shared battle network with one command, so that the two trainees can reach the other team's web without manually assembling Terraform and Ansible files.

## RED and GREEN

- RED commit: `d976595` added tests for the missing `battlectl.py`; all four new tests failed because the tool did not exist.
- GREEN: `py -3 -m unittest discover -s tests -v` ran 26 tests and all passed.
- Terraform: `terraform validate` succeeded and `terraform test` passed all five mock runs.
- Coverage: `coverage run --source=app,battle-network -m unittest discover -s tests` followed by `coverage report --fail-under=80` reported 84% total coverage.

## Guarantees

| What is guaranteed | Test | Type | Result |
|---|---|---|---|
| Runtime files contain exactly two team mappings and do not leak SSH paths into Terraform variables | `test_prepare_writes_terraform_and_inventory_for_two_sandboxes` | unit | PASS |
| Duplicate VM IDs and missing management SSH configs stop deployment before cloud changes | `test_validate_rejects_duplicate_ids_and_missing_ssh_config` | unit | PASS |
| Deployment uses a saved Terraform plan and the generated Ansible inventory without a shell command string | `test_commands_use_saved_plan_and_generated_inventory_without_shell` | unit | PASS |
| Operator docs use branch `main` and expose plan/deploy commands | `test_operator_guide_uses_main_and_one_command_battle_tool` | documentation contract | PASS |
| The shared network has no DHCP/gateway and exposes only ICMP and TCP 8080 | `terraform test` / `shared_network_without_hub` | infrastructure mock | PASS |

## Known deployment boundary

The tests do not create resources in the target OpenStack cloud. A real deployment still requires actual pool/sandbox/Nova UUIDs, two instructor management SSH configs, OpenStack credentials with interface-attach rights, and four VMs in the same OpenStack project. The CyberRangeCZ per-run topology only draws the assigned sandbox; the externally attached battle NIC is verified by connectivity and sandbox UUID, not by a cross-sandbox edge in that UI.
