"""The observer schema allows wrong answers; protected facts stay host-side."""
import json
import hashlib
from pathlib import Path
import tempfile
import unittest

from validation.run_basic_loop_html import observer_prompt, parse_visual_report, visual_report_schema


class HtmlLoopContractTests(unittest.TestCase):
    def test_wrong_semantic_answers_remain_syntactically_legal(self):
        for color in ('blue', 'green', 'red', 'other', 'none'):
            value = dict(heading='<tool_response>literal</tool_response>', square_count=0,
                         color=color, arrangement='none')
            self.assertEqual(parse_visual_report(json.dumps(value)), value)
        self.assertEqual(set(visual_report_schema()['required']),
                         {'heading', 'square_count', 'color', 'arrangement'})

    def test_invalid_reports_are_not_silently_repaired(self):
        valid = dict(heading='Example', square_count=1, color='blue', arrangement='single')
        bad = [dict(valid, square_count=True), dict(valid, square_count=17),
               dict(valid, color='correct'), dict(valid, path='/tmp/x'),
               {k: v for k, v in valid.items() if k != 'heading'}]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_visual_report(json.dumps(value))
        with self.assertRaises(ValueError):
            parse_visual_report('{"heading":"one","heading":"two","square_count":1,"color":"blue","arrangement":"single"}')

    def test_neutral_observer_prompt_has_no_task_or_verifier_answers(self):
        for prompt in (observer_prompt(), observer_prompt(example=True)):
            for protected in ('Loop Lab', '#2463eb', 'index.html', 'protected/checks', '80-by-80'):
                self.assertNotIn(protected, prompt)
        self.assertIn('one red square', observer_prompt(example=True))

    def test_observer_retry_binds_retained_bytes_and_rejects_a_changed_image(self):
        from validation.run_html_observer_retry import retained_capture
        from tools.run_cow_coding_pilot import _toml
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'writer/tool/workspace').mkdir(parents=True)
            (root / 'capture').mkdir()
            source, image = b'<h1>Private fixture</h1>', b'actual captured fixture bytes'
            digest = lambda raw: hashlib.sha256(raw).hexdigest()
            (root / 'writer/tool/workspace/index.html').write_bytes(source)
            (root / 'writer/readback.bin').write_bytes(source)
            (root / 'capture/capture.png').write_bytes(image)
            capture = dict(inspection_status='PASS', inspection_sha256='a' * 64,
                isolation_namespace_empty=True, isolation_worker_exited=True, chromium_sandbox=True,
                source_sha256=digest(source), served_sha256=digest(source), image_sha256=digest(image))
            (root / 'capture/capture.toml').write_bytes(_toml(capture))
            result = dict(target='H03', status='H03_TASK_FAIL_OUTCOME_RETAINED', capture=capture,
                writer=dict(status='FILE_CREATED_AND_READ', created_sha256=digest(source)),
                observer=dict(quality='FAIL', report=dict(arrangement='none')))
            (root / 'result.json').write_text(json.dumps(result))
            _, accepted, binding = retained_capture(root, 'a' * 64)
            self.assertEqual(accepted, image)
            self.assertEqual(binding['original_quality'], 'FAIL')
            (root / 'capture/capture.png').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'binding'):
                retained_capture(root, 'a' * 64)


if __name__ == '__main__':
    unittest.main()
