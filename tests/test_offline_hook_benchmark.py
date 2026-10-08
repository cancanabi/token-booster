import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from offline_hook_benchmark import evaluate

class OfflineBenchmarkTests(unittest.TestCase):
    def test_all_contract_cases(self):
        result = evaluate()
        self.assertTrue(result['pass'], result)
        self.assertEqual(result['test_cases'], 11)

    def test_failure_outputs_never_rewritten(self):
        cases = {x['case']: x for x in evaluate()['cases']}
        for name in ('failing_test', 'stderr_present', 'warning_present', 'unsafe_command', 'shell_pipeline', 'interrupted'):
            self.assertFalse(cases[name]['rewritten'], name)
            self.assertEqual(cases[name]['reduction_percent'], 0)

    def test_benign_large_success_compresses(self):
        case = next(x for x in evaluate()['cases'] if x['case'] == 'successful_test')
        self.assertTrue(case['rewritten'])
        self.assertGreater(case['reduction_percent'], 30)

if __name__ == '__main__':
    unittest.main()
