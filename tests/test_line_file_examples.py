"""New-root teaching follows the explicit line-file tool contract."""
import json,tempfile,unittest
from pathlib import Path
from branchwrite.coding_defaults import system_prefix
from branchwrite.execution import Executor,Grant
from branchwrite.tool_registry import ToolRegistry
FILE=Path(__file__).resolve().parents[1]/"examples/line-file-worked-examples.txt"
def sections():return FILE.read_text().split("## Line file example ")[1:]

class LineFileExampleTests(unittest.TestCase):
 def registry(self,root,path="new/file.txt",repair=False):
  source=root/"source";source.mkdir();(source/"keep.txt").write_bytes(b"keep\n")
  executor=Executor.create(source,root/"world")
  return executor,ToolRegistry(executor,Grant((path,) if repair else (),False,create_paths=(path,),read_paths=(path,)))
 def test_actual_tool_schema_selects_new_line_examples(self):
  with tempfile.TemporaryDirectory() as tmp:
   _,registry=self.registry(Path(tmp))
   text=system_prefix(registry.model_schema())
   self.assertIn("# Text files with explicit lines",text)
   self.assertNotIn("# Literal file operations",text)
   self.assertIn("final_newline",text);self.assertIn("full file",text)
 def test_synthetic_old_create_schema_keeps_old_teaching(self):
  text=system_prefix({"oneOf":[{"properties":{"tool":{"enum":["create_file"]}}}]})
  self.assertIn("# Literal file operations",text);self.assertNotIn("# Text files with explicit lines",text)
 def test_each_example_replays_actual_tools_and_exact_readback(self):
  self.assertEqual(len(sections()),3)
  for part in sections():
   spec=json.loads(next(l[6:] for l in part.splitlines() if l.startswith("TASK: ")))
   actions=[json.loads(l[8:]) for l in part.splitlines() if l.startswith("ACTION: ")]
   feedback=[json.loads(l[10:]) for l in part.splitlines() if l.startswith("FEEDBACK: ")]
   with self.subTest(case=spec["title"]),tempfile.TemporaryDirectory() as tmp:
    executor,registry=self.registry(Path(tmp),spec["path"],spec["repair"]);observations=();readbacks=[]
    self.assertEqual(len(actions),len(feedback))
    for index,(action,wanted) in enumerate(zip(actions,feedback)):
     result=registry.execute(registry.freeze(json.dumps(action),observations=observations),"line-example-"+str(index))
     if result.observation is not None:observations+=(result.observation,)
     self.assertEqual(result.disposition,wanted["disposition"])
     self.assertEqual(result.stdout,wanted["stdout"].encode());self.assertEqual(result.stderr,wanted["stderr"].encode())
     if action["tool"]=="read_file":readbacks.append(result.stdout)
    expected=bytes.fromhex(spec["utf8_hex"])
    self.assertTrue(readbacks);self.assertEqual(readbacks[-1],expected)
    self.assertEqual((executor.workspace/spec["path"]).read_bytes(),expected)
    self.assertEqual((executor.workspace/"keep.txt").read_bytes(),b"keep\n")
    self.assertEqual(sorted(p.relative_to(executor.workspace).as_posix() for p in executor.workspace.rglob("*") if p.is_file()),sorted(["keep.txt",spec["path"]]))
 def test_creation_and_repair_use_line_arrays_with_explicit_endings(self):
  for part in sections():
   actions=[json.loads(l[8:]) for l in part.splitlines() if l.startswith("ACTION: ")]
   self.assertEqual(actions[0]["tool"],"create_text_file")
   for action in actions:
    if action["tool"] in ["create_text_file","replace_text_file"]:
     args=action["arguments"];self.assertIs(type(args["lines"]),list);self.assertIs(type(args["final_newline"]),bool)
     self.assertIn(args["line_ending"],["LF","CRLF"])
     self.assertTrue(all("\n" not in line and "\r" not in line for line in args["lines"]))
  repair=next(s for s in sections() if '"repair": true' in s)
  self.assertEqual([json.loads(l[8:])["tool"] for l in repair.splitlines() if l.startswith("ACTION: ")],["create_text_file","read_file","replace_text_file","read_file","finish"])
 def test_protected_task_and_answer_are_not_in_generic_examples(self):
  text=FILE.read_text()
  for forbidden in ["literal data/hello.txt","hello 'Ubuntu' $HOME"]:self.assertNotIn(forbidden,text)
