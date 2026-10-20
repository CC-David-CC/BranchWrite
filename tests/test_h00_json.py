"""JSON H00 is an opt-in model-output arm, not a second workflow ledger."""
import json
from pathlib import Path
import tempfile
import unittest

from tests.test_cow_coding_pilot import ScriptedClient
from tools.run_cow_coding_pilot import CodingPilot, FileTask


class H00JsonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bw-h00-json-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.task = FileTask("H00", self.source, "hello.txt", "Create a greeting and read it back.")

    def run_case(self, text, *, complete=True):
        client = ScriptedClient(text)
        normal = client._result
        client._result = lambda text, **kwargs: normal(text, complete=complete)
        pilot = CodingPilot(client, self.root / "run", eos_tokens=(99,), max_tokens=128)
        return client, pilot.run_create_read(self.task, output_format="json_schema")

    def test_json_action_creates_and_reads_actual_bytes(self):
        client, result = self.run_case(json.dumps({"tool": "create_file", "arguments": {
            "path": "hello.txt", "content": "Hello, loop.\n"}}))
        self.assertEqual(result.status, "FILE_CREATED_AND_READ")
        self.assertEqual((self.root / "run/tool/workspace/hello.txt").read_bytes(), b"Hello, loop.\n")
        self.assertEqual((self.root / "run/readback.bin").read_bytes(), b"Hello, loop.\n")
        self.assertEqual(result.readback_bytes, 13)
        self.assertEqual(result.created_sha256, result.readback_sha256)
        options = next(row[1] for row in client.calls if row[0] == "answer")
        self.assertEqual(options["grammar_state"], "BW_H00_JSON")
        self.assertEqual(sum(row[0] == "answer" for row in client.calls), 1)
        prompt = next(row[1] for row in client.calls if row[0] == "prepare")
        self.assertNotIn("Hello, loop.", prompt)
        self.assertNotIn(".bw literal", prompt)
        self.assertFalse((self.source / "hello.txt").exists())

    def test_host_rejects_wrong_tool_even_if_json_is_valid(self):
        _, result = self.run_case('{"tool":"delete_file","arguments":{"path":"hello.txt","content":"x"}}')
        self.assertEqual(result.status, "FORMAT_REJECTED")
        self.assertFalse((self.root / "run/tool/workspace/hello.txt").exists())

    def test_host_rejects_wrong_path(self):
        _, result = self.run_case('{"tool":"create_file","arguments":{"path":"../outside","content":"x"}}')
        self.assertEqual(result.status, "FORMAT_REJECTED")
        self.assertFalse((self.root / "run/tool/workspace/hello.txt").exists())

    def test_host_rejects_wrong_argument_type(self):
        _, result = self.run_case('{"tool":"create_file","arguments":{"path":"hello.txt","content":3}}')
        self.assertEqual(result.status, "FORMAT_REJECTED")
        self.assertFalse((self.root / "run/tool/workspace/hello.txt").exists())

    def test_duplicate_keys_are_not_silently_accepted(self):
        _, result = self.run_case('{"tool":"delete_file","tool":"create_file","arguments":{"path":"hello.txt","content":"x"}}')
        self.assertEqual(result.status, "FORMAT_REJECTED")
        self.assertFalse((self.root / "run/tool/workspace/hello.txt").exists())

    def test_additional_argument_is_rejected(self):
        _, result = self.run_case('{"tool":"create_file","arguments":{"path":"hello.txt","content":"x","execute":true}}')
        self.assertEqual(result.status, "FORMAT_REJECTED")
        self.assertFalse((self.root / "run/tool/workspace/hello.txt").exists())

    def test_well_formed_partial_output_is_not_executed(self):
        _, result = self.run_case('{"tool":"create_file","arguments":{"path":"hello.txt","content":"x"}}', complete=False)
        self.assertEqual(result.status, "OUTPUT_INCOMPLETE")
        self.assertFalse((self.root / "run/tool/workspace/hello.txt").exists())

    def test_schema_requires_fields_but_does_not_supply_answer(self):
        from tools.run_cow_coding_pilot import create_file_schema
        schema = create_file_schema("hello.txt")
        self.assertEqual(schema["required"], ["tool", "arguments"])
        arguments = schema["properties"]["arguments"]
        self.assertEqual(arguments["required"], ["path", "content"])
        self.assertEqual(arguments["properties"]["content"]["type"], "string")
        self.assertNotIn("enum", arguments["properties"]["content"])
        self.assertNotIn("const", arguments["properties"]["content"])
        self.assertFalse(schema["additionalProperties"])
        self.assertFalse(arguments["additionalProperties"])


if __name__ == "__main__":
    unittest.main()
