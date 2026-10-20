"""Create/read callers select a registered output contract independently of H00."""
import json
from pathlib import Path
import tempfile
import unittest

from test_cow_coding_pilot import ScriptedClient
from tools.run_cow_coding_pilot import CodingPilot, FileTask


class HtmlCreateGrammarTests(unittest.TestCase):
    def test_html_create_uses_explicit_host_grammar_and_real_readback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'empty'
            source.mkdir()
            html = '<h1>A model-written heading</h1>\n'
            client = ScriptedClient(json.dumps(dict(tool='create_file', arguments=dict(path='index.html', content=html))))
            pilot = CodingPilot(client, root / 'run', eos_tokens=(99,))
            result = pilot.run_create_read(FileTask('H03', source, 'index.html', 'Create a page.'),
                output_format='json_schema', grammar_state='BW_CREATE_HTML')
            self.assertEqual(result.status, 'FILE_CREATED_AND_READ')
            self.assertEqual((root / 'run/readback.bin').read_bytes(), html.encode())
            answer = next(row for row in client.calls if row[0] == 'answer')
            self.assertEqual(answer[1]['grammar_state'], 'BW_CREATE_HTML')


if __name__ == '__main__':
    unittest.main()
