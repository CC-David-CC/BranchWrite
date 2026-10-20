"""Independent terminal components before any autonomous model run."""
from pathlib import Path
import tempfile,unittest
from branchwrite.terminal_components import DOMAINS, build_case, run_case

class TerminalComponentTests(unittest.TestCase):
 def test_seeded_split_reproducibility_and_independence(self):
  for domain in DOMAINS:
   a=build_case(domain,seed=731,split="demo")
   self.assertEqual(a,build_case(domain,seed=731,split="demo"))
   b=build_case(domain,seed=731,split="heldout")
   self.assertNotEqual(a,b)
   self.assertNotEqual([x["command"] for x in a["steps"]],[x["command"] for x in b["steps"]])
 def test_reject_unknown_inputs_before_execution(self):
  for kwargs in [dict(domain="unknown"),dict(domain="streams",split="bogus"),dict(domain="streams",seed=True),dict(domain="streams",seed=-1)]:
   with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):build_case(**kwargs)
 def test_altered_expectation_rejects_before_directory_creation(self):
  with tempfile.TemporaryDirectory() as t:
   case=build_case("streams");case["steps"][0]["expected"]["exit_code"]=0
   output=Path(t)/"must-not-exist"
   with self.assertRaises(ValueError):run_case(case,output)
   self.assertFalse(output.exists())
 def run_component(self,domain):
  with tempfile.TemporaryDirectory() as t:
   path=Path(t)/"case"
   result=run_case(build_case(domain,seed=731,split="heldout"),path)
   self.assertEqual(result["status"],"PASS",result)
   self.assertFalse(result["model_inference"])
   self.assertTrue((path/"result.json").is_file())
   for row in result["observations"]:
    self.assertEqual(row["status"],"PASS",row)
    self.assertTrue(row["isolation"]["worker_exited"])
    self.assertEqual(row["isolation"]["namespace_members_after"],[])
    for field in ("stdout","stderr"):
     self.assertEqual(row["actual"][field]["bytes"],row["feedback"][field+"_artifact"]["bytes"])
     self.assertEqual(row["actual"][field]["sha256"],row["feedback"][field+"_artifact"]["sha256"])
     self.assertFalse(row["feedback"][field+"_truncated"])
   with self.assertRaises(FileExistsError):run_case(build_case(domain,seed=731,split="heldout"),path)
 def test_streams(self):self.run_component("streams")
 def test_warning_success(self):self.run_component("warning-success")
 def test_pipeline(self):self.run_component("pipeline")
 def test_binary_invalid_utf8(self):self.run_component("binary")
 def test_literal_replacement_character(self):self.run_component("literal-ufffd")
 def test_empty_streams(self):self.run_component("empty")
 def test_missing_versus_empty_file(self):self.run_component("missing-file")
 def test_unicode_quoting(self):self.run_component("quoting")
 def test_final_newlines(self):self.run_component("newlines")
 def test_timeout(self):self.run_component("timeout")
 def test_command_not_found_recovery(self):self.run_component("recovery")

if __name__=="__main__":unittest.main()
