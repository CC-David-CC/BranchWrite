import json
import unittest

from branchwrite.learning_cli import main


class LearningLevelsCliTests(unittest.TestCase):
    def test_lists_s3_modes_without_a_cow_connection(self):
        output = []
        result = main(['levels'], output=output.append)
        self.assertEqual(result, 0)
        self.assertEqual(len(output), 1)
        value = json.loads(output[0])
        self.assertEqual(value['kind'], 'bw.sss-response-levels.v1')
        self.assertEqual(value['levels']['answer']['direct']['target_policy'], 'answer_only')
        self.assertEqual(value['levels']['answer']['reasoning']['target_policy'],
                         'reasoning_and_answer')
        self.assertIn('independent reasoning checker',
                      value['levels']['answer']['reasoning']['requires'])
        self.assertEqual(value['levels']['format']['direct']['target_policy'], 'format_only')
        self.assertEqual(value['levels']['composed']['direct']['target_policy'],
                         'answer_and_format')
        self.assertEqual(value['levels']['composed']['reasoning']['target_policy'],
                         'reasoning_answer_and_format')
        self.assertFalse(value['ownership']['automatic_training'])


if __name__ == '__main__':
    unittest.main()
