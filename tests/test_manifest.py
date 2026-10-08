import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class ManifestTests(unittest.TestCase):
    def test_plugin_manifest(self):
        m = json.loads((ROOT/'.claude-plugin/plugin.json').read_text())
        self.assertEqual(m['name'], 'token-booster')
        self.assertEqual(m['version'], '5.0.1')
    def test_hook_schema(self):
        cfg = json.loads((ROOT/'hooks/hooks.json').read_text())
        entry = cfg['hooks']['PostToolUse'][0]
        self.assertEqual(entry['matcher'], 'Bash')
        hook = entry['hooks'][0]
        self.assertIn('python3', hook['command'])
        self.assertIn('post_tool_use.py', hook['command'])
        self.assertNotIn('args', hook)
    def test_skills_are_on_demand(self):
        for path in (ROOT/'skills').glob('*/SKILL.md'):
            text = path.read_text(encoding='utf-8')
            self.assertIn('disable-model-invocation: true', text, path.name)
    def test_no_surprise_plugin_network_config(self):
        self.assertFalse((ROOT/'.mcp.json').exists())
        self.assertFalse((ROOT/'settings.json').exists())

if __name__ == '__main__':
    unittest.main()

class V5HooksTests(unittest.TestCase):
    def test_read_hooks_wired_and_portable(self):
        cfg = json.loads((ROOT/'hooks/hooks.json').read_text())['hooks']
        read_post = [x for x in cfg['PostToolUse'] if x['matcher'] == 'Read']
        read_pre = [x for x in cfg['PreToolUse'] if x['matcher'] == 'Read']
        self.assertEqual(len(read_post), 1)
        self.assertEqual(len(read_pre), 1)
        self.assertEqual(len(cfg['SessionStart']), 1)
        for group in (read_post, read_pre, cfg['SessionStart']):
            self.assertIn('${CLAUDE_PLUGIN_ROOT}', group[0]['hooks'][0]['command'])
            self.assertIn('read_cache_hook.py', group[0]['hooks'][0]['command'])
    def test_v5_skills_on_demand(self):
        for name in ('cache','doctor'):
            self.assertIn('disable-model-invocation: true',(ROOT/'skills'/name/'SKILL.md').read_text())
