"""Executable teaching examples use actual file tools; no model/GPU claim."""
import json,tempfile,unittest
from pathlib import Path
from branchwrite.coding_defaults import system_prefix
from branchwrite.execution import Executor,Grant,ToolRejected
from branchwrite.tool_registry import ToolRegistry

EXAMPLES=Path(__file__).resolve().parents[1]/"examples/literal-file-worked-examples.txt"

def sections():
    return EXAMPLES.read_text().split("## Literal file example ")[1:]

class LiteralFileExamplesTests(unittest.TestCase):
    def test_create_grant_selects_literal_teaching(self):
        text=system_prefix({"oneOf":[{"properties":{"tool":{"enum":["create_file"]}}}]})
        self.assertIn("# Literal file operations",text)
        self.assertIn("Do not add indentation",text)
    def test_no_create_grant_preserves_existing_prefix(self):
        text=system_prefix({"oneOf":[{"properties":{"tool":{"enum":["read_file"]}}}]})
        self.assertNotIn("# Literal file operations",text)
        self.assertEqual(text.count("## Worked example "),3)
    def test_examples_execute_with_exact_bytes_and_real_readback(self):
        self.assertEqual(len(sections()),3)
        for number,section in enumerate(sections()):
            with self.subTest(example=number),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);source=root/"source";source.mkdir();(source/"neighbor.txt").write_bytes(b"keep\n")
                specification=json.loads(next(l[6:] for l in section.splitlines() if l.startswith("TASK: ")))
                path=specification["path"];expected=bytes.fromhex(specification["utf8_hex"])
                executor=Executor.create(source,root/"world")
                grant=Grant((path,) if specification["repair"] else (),False,create_paths=(path,),read_paths=(path,))
                registry=ToolRegistry(executor,grant)
                actions=[json.loads(l[8:]) for l in section.splitlines() if l.startswith("ACTION: ")]
                feedback=[json.loads(l[10:]) for l in section.splitlines() if l.startswith("FEEDBACK: ")]
                self.assertEqual(len(actions),len(feedback));reads=[];observations=()
                for index,(action,wanted) in enumerate(zip(actions,feedback)):
                    result=registry.execute(registry.freeze(json.dumps(action),observations=observations),"example-"+str(index))
                    if result.observation is not None:observations+=(result.observation,)
                    self.assertEqual(result.disposition,wanted["disposition"])
                    self.assertEqual(result.exit_code,wanted["exit_code"])
                    self.assertEqual(result.stdout,wanted["stdout"].encode())
                    self.assertEqual(result.stderr,wanted["stderr"].encode())
                    if action["tool"]=="read_file":reads.append(result.stdout)
                self.assertTrue(reads);self.assertEqual(reads[-1],expected)
                self.assertEqual((executor.workspace/path).read_bytes(),expected)
                self.assertEqual((executor.workspace/"neighbor.txt").read_bytes(),b"keep\n")
                self.assertEqual(sorted(str(p.relative_to(executor.workspace)) for p in executor.workspace.rglob("*") if p.is_file()),sorted(["neighbor.txt",path]))
    def test_unicode_and_line_ending_distinctions_are_present(self):
        specs=[json.loads(next(l[6:] for l in section.splitlines() if l.startswith("TASK: "))) for section in sections()]
        bodies=[bytes.fromhex(s["utf8_hex"]) for s in specs]
        self.assertTrue(any(b"e\xcc\x81" in b and b"\xc3\xa9" in b for b in bodies))
        self.assertTrue(any(b"\r\n" in b and not b.endswith(b"\n") for b in bodies))
        self.assertTrue(any(b.endswith(b"\n") and not b.endswith(b"\n\n") for b in bodies))
    def test_repair_example_reads_before_replacing(self):
        section=next(s for s in sections() if '"repair": true' in s)
        actions=[json.loads(l[8:]) for l in section.splitlines() if l.startswith("ACTION: ")]
        self.assertEqual([a["tool"] for a in actions],["create_file","read_file","replace","read_file","finish"])
        self.assertNotEqual(actions[0]["arguments"]["content"],bytes.fromhex(json.loads(next(l[6:] for l in section.splitlines() if l.startswith("TASK: ")))["utf8_hex"]).decode())
    def test_teaching_does_not_embed_protected_l02_answer(self):
        text=EXAMPLES.read_text()
        for forbidden in ["literal data/hello.txt","hello 'Ubuntu' $HOME","1b6c0b0f6bcce5"]:
            self.assertNotIn(forbidden,text)
