import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from branchwrite.lesson_cli import main as lesson_main
from sss.adapters.episode_lessons import pcc_lesson


class LearningLevelHandoffTests(unittest.TestCase):
    def test_bw_submits_sss_response_level_lesson_without_rewriting_it(self):
        contract = 'a' * 64
        segments = [
            dict(role='user', kind='question', rendered='USER: return JSON',
                 verified=False, scope='practice'),
            dict(role='assistant', kind='format', rendered='{"answer":"7"}',
                 verified=True, scope='practice'),
        ]
        lesson = pcc_lesson(
            'format only', contract, segments,
            archive_sha256='b' * 64, verification_sha256='c' * 64,
            renderer_sha256='d' * 64, tokenizer_sha256='e' * 64,
            skill_id='math.add.no_carry', target_policy='format_only')

        class Client:
            def __init__(self):
                self.request = None

            def training_submit(self, path, body, operation_id):
                self.request = (path, body, operation_id)
                return dict(lesson_id='admitted-lesson')

        client = Client()
        output = []
        with tempfile.TemporaryDirectory() as temporary:
            file = Path(temporary) / 'lesson.json'
            file.write_text(json.dumps(lesson), encoding='utf-8')
            with patch('branchwrite.lesson_cli._client',
                       return_value=(dict(model_contract_id=contract), client)):
                result = lesson_main(['submit', str(file), '--operation-id', 'format-lesson'],
                                     output=output.append)

        self.assertEqual(result, 0)
        self.assertEqual(client.request, ('lessons', dict(lesson=lesson), 'format-lesson'))
        self.assertEqual(json.loads(output[0])['lesson_id'], 'admitted-lesson')


if __name__ == '__main__':
    unittest.main()
