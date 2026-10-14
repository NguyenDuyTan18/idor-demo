import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BattleControlTests(unittest.TestCase):
    def setUp(self):
        source = ROOT / 'battle-network/battlectl.py'
        self.assertTrue(source.is_file(), 'The one-command battle deployment tool is required')
        spec = importlib.util.spec_from_file_location('battlectl', source)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.ssh_a = root / 'team-a-management-config'
        self.ssh_b = root / 'team-b-management-config'
        self.ssh_a.write_text('Host kali\n')
        self.ssh_b.write_text('Host kali\n')
        self.config = {
            'cloud_name': 'instructor-cloud',
            'pool_id': 7,
            'teams': {
                'A': {
                    'sandbox_uuid': '00000000-0000-4000-8000-000000000001',
                    'kali_server_id': '10000000-0000-4000-8000-000000000001',
                    'web_server_id': '20000000-0000-4000-8000-000000000002',
                    'management_ssh_config': str(self.ssh_a),
                },
                'B': {
                    'sandbox_uuid': '00000000-0000-4000-8000-000000000002',
                    'kali_server_id': '30000000-0000-4000-8000-000000000003',
                    'web_server_id': '40000000-0000-4000-8000-000000000004',
                    'management_ssh_config': str(self.ssh_b),
                },
            },
        }

    def test_prepare_writes_terraform_and_inventory_for_two_sandboxes(self):
        runtime = Path(self.temp.name) / 'runtime'
        self.module.prepare(self.config, runtime)

        tfvars = json.loads((runtime / 'terraform.auto.tfvars.json').read_text())
        self.assertEqual(tfvars['pool_id'], 7)
        self.assertEqual(set(tfvars['teams']), {'A', 'B'})
        self.assertNotIn('management_ssh_config', tfvars['teams']['A'])

        inventory = (runtime / 'inventory.yml').read_text()
        self.assertIn(str(self.ssh_a).replace('\\', '/'), inventory)
        self.assertIn(str(self.ssh_b).replace('\\', '/'), inventory)
        self.assertIn('team-a-kali:', inventory)
        self.assertIn('team-b-web:', inventory)

    def test_validate_rejects_duplicate_ids_and_missing_ssh_config(self):
        self.config['teams']['B']['web_server_id'] = self.config['teams']['A']['web_server_id']
        with self.assertRaisesRegex(ValueError, 'distinct'):
            self.module.validate_config(self.config)

        self.config['teams']['B']['web_server_id'] = '40000000-0000-4000-8000-000000000004'
        self.config['teams']['B']['management_ssh_config'] = str(Path(self.temp.name) / 'missing')
        with self.assertRaisesRegex(ValueError, 'SSH config'):
            self.module.validate_config(self.config)

    def test_commands_use_saved_plan_and_generated_inventory_without_shell(self):
        runtime = Path(self.temp.name) / 'runtime'
        plan_commands = self.module.commands_for('plan', runtime)
        deploy_commands = self.module.commands_for('deploy', runtime)
        self.assertEqual(plan_commands[0][-2:], ['-chdir=' + str(ROOT / 'battle-network/terraform'), 'init'])
        self.assertTrue(any(part.endswith('battle.tfplan') for part in plan_commands[-1]))
        self.assertFalse(any('plan' in command for command in deploy_commands))
        self.assertEqual(deploy_commands[2][2], 'apply')
        self.assertTrue(deploy_commands[2][-1].endswith('battle.tfplan'))
        self.assertEqual(deploy_commands[-1][0], 'ansible-playbook')
        self.assertIn(str(runtime / 'inventory.yml'), deploy_commands[-1])

    def test_example_config_is_valid_json_with_placeholders(self):
        example = json.loads((ROOT / 'battle-network/battle-config.example.json').read_text())
        self.assertEqual(set(example['teams']), {'A', 'B'})
        self.assertEqual(example['pool_id'], 1)

    def test_deploy_requires_a_reviewed_plan_for_the_same_config(self):
        runtime = Path(self.temp.name) / 'runtime'
        runtime.mkdir()
        with self.assertRaisesRegex(ValueError, 'plan'):
            self.module.require_reviewed_plan(self.config, runtime)

        (runtime / 'battle.tfplan').write_bytes(b'plan')
        (runtime / 'reviewed-config.json').write_text(
            json.dumps(self.config, sort_keys=True), encoding='utf-8')
        self.module.require_reviewed_plan(self.config, runtime)
        changed = json.loads(json.dumps(self.config))
        changed['pool_id'] = 8
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.module.require_reviewed_plan(changed, runtime)


if __name__ == '__main__':
    unittest.main()
