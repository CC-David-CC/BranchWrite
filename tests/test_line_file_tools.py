"""Real filesystem contracts for explicit line-based text tools; CPU only."""
import hashlib,json,os,stat,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from branchwrite.execution import Executor,Grant,ToolRejected
from branchwrite.tool_registry import ToolRegistry,EffectIndeterminate

class LineFileToolsTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  source=self.root/"source";source.mkdir();(source/"keep.txt").write_bytes(b"keep\n")
  self.ex=Executor.create(source,self.root/"world");self.path="notes/session/data.txt"
  self.grant=Grant((self.path,),False,create_paths=(self.path,),read_paths=(self.path,))
  self.reg=ToolRegistry(self.ex,self.grant)
 def args(self,lines=None,**changes):
  result=dict(path=self.path,lines=["first 'line' $HOME","second: \u0394 \u00e9 e\u0301"] if lines is None else lines,line_ending="LF",final_newline=True)
  result.update(changes);return result
 def freeze(self,tool="create_text_file",observations=(),**changes):
  return self.reg.freeze(json.dumps(dict(tool=tool,arguments=self.args(**changes))),observations=observations)
 def create(self,**changes):
  return self.reg.execute(self.freeze(**changes),"create-lines")
 def read(self):
  return self.reg.execute(self.reg.freeze(json.dumps(dict(tool="read_file",arguments=dict(path=self.path)))),"read-lines")
 def test_schema_has_typed_lines_explicit_endings_and_boolean(self):
  variants={v["properties"]["tool"]["enum"][0]:v for v in self.reg.model_schema()["oneOf"]}
  for tool in ["create_text_file","replace_text_file"]:
   self.assertIn(tool,variants)
   props=variants[tool]["properties"]["arguments"]["properties"]
   self.assertEqual(props["lines"]["type"],"array");self.assertEqual(props["lines"]["items"]["type"],"string")
   self.assertEqual(props["line_ending"]["enum"],["LF","CRLF"]);self.assertEqual(props["final_newline"]["type"],"boolean")
 def test_schema_keeps_unicode_representations_and_host_rejects_embedded_breaks(self):
  variant=next(v for v in self.reg.model_schema()['oneOf'] if v['properties']['tool']['enum']==['create_text_file'])
  item=variant['properties']['arguments']['properties']['lines']['items']
  self.assertNotIn('pattern',item)
  with self.assertRaisesRegex(ToolRejected,'line'):self.freeze(lines=['a\nb'])
  self.assertFalse((self.ex.workspace/'notes').exists())
 def test_plan_does_not_make_missing_parents(self):
  self.freeze();self.assertFalse((self.ex.workspace/"notes").exists())
 def test_create_and_read_preserve_exact_unicode_and_literal_dollars(self):
  self.create();read=self.read();expected="first 'line' $HOME\nsecond: \u0394 \u00e9 e\u0301\n".encode()
  self.assertEqual(read.stdout,expected);self.assertEqual(read.observation.sha256,hashlib.sha256(expected).hexdigest())
  self.assertEqual((self.ex.workspace/"keep.txt").read_bytes(),b"keep\n")
 def test_crlf_and_no_final_newline_are_explicit(self):
  self.create(lines=["a","b"],line_ending="CRLF",final_newline=False)
  self.assertEqual(self.read().stdout,b"a\r\nb")
 def test_blank_lines_and_final_crlf_are_not_trimmed(self):
  self.create(lines=[" a ","","b"],line_ending="CRLF")
  self.assertEqual(self.read().stdout,b" a \r\n\r\nb\r\n")
 def test_empty_file_then_observed_full_replacement(self):
  self.create(lines=[],final_newline=False);observed=self.read().observation
  plan=self.freeze("replace_text_file",observations=(observed,),lines=["nonempty"])
  self.reg.execute(plan,"fill-empty");self.assertEqual(self.read().stdout,b"nonempty\n")
 def test_replacement_requires_latest_visible_source(self):
  self.create()
  with self.assertRaisesRegex(ToolRejected,"read|observ"):self.freeze("replace_text_file",lines=["changed"])
  observed=self.read().observation
  self.reg.execute(self.freeze("replace_text_file",observations=(observed,),lines=["changed"]),"edit-lines")
  self.assertEqual(self.read().stdout,b"changed\n")
  with self.assertRaisesRegex(ToolRejected,"stale"):self.freeze("replace_text_file",observations=(observed,),lines=["bad"])
 def test_creation_never_overwrites_an_existing_name(self):
  self.create();before=(self.ex.workspace/self.path).read_bytes()
  with self.assertRaisesRegex(ToolRejected,"exists|stale"):self.freeze()
  self.assertEqual((self.ex.workspace/self.path).read_bytes(),before)
 def test_derived_text_tool_does_not_expand_host_grants(self):
  wrong=self.args(path="outside/no.txt")
  with self.assertRaisesRegex(ToolRejected,"grant"):self.reg.freeze(json.dumps(dict(tool="create_text_file",arguments=wrong)))
  self.assertFalse((self.ex.workspace/"outside").exists())
  create_only=ToolRegistry(self.ex,Grant((),False,create_paths=(self.path,),read_paths=(self.path,)))
  names=[v["properties"]["tool"]["enum"][0] for v in create_only.model_schema()["oneOf"]]
  self.assertIn("create_text_file",names);self.assertNotIn("replace_text_file",names)
 def test_embedded_lf_or_cr_in_a_line_is_rejected_without_effects(self):
  for value in ["a\nb","a\rb"]:
   with self.subTest(value=value),self.assertRaisesRegex(ToolRejected,"line|newline"):self.freeze(lines=[value])
  self.assertFalse((self.ex.workspace/"notes").exists())
 def test_wrong_types_endings_and_ambiguous_empty_terminator_are_rejected(self):
  for changes in [dict(lines="not-array"),dict(lines=[1]),dict(final_newline=1),dict(line_ending="AUTO"),dict(lines=[],final_newline=True)]:
   with self.subTest(changes=changes),self.assertRaisesRegex(ToolRejected,"line|type|boolean|ending|empty"):self.freeze(**changes)
  self.assertFalse((self.ex.workspace/"notes").exists())
 def test_false_final_newline_cannot_hide_a_trailing_empty_element(self):
  with self.assertRaisesRegex(ToolRejected,'empty|final_newline'):self.freeze(lines=['a',''],final_newline=False)
  self.assertFalse((self.ex.workspace/'notes').exists())
 def test_combined_utf8_byte_bound_applies_before_directory_creation(self):
  with self.assertRaisesRegex(ToolRejected,"bound|limit"):self.freeze(lines=["\u0394"*17000])
  self.assertFalse((self.ex.workspace/"notes").exists())
 def test_symlink_parent_is_rejected_before_write(self):
  outside=self.root/"outside";outside.mkdir();(self.ex.workspace/"notes").symlink_to(outside,target_is_directory=True)
  with self.assertRaisesRegex(ToolRejected,"link|parent|directory"):self.freeze()
  self.assertEqual(list(outside.iterdir()),[])
 def test_full_replacement_preserves_mode_and_neighbors(self):
  self.create(lines=["old"]);leaf=self.ex.workspace/self.path;leaf.chmod(0o640);observed=self.read().observation
  self.reg.execute(self.freeze("replace_text_file",observations=(observed,),lines=["new"],final_newline=False),"replace-file")
  self.assertEqual(leaf.read_bytes(),b"new");self.assertEqual(stat.S_IMODE(leaf.stat().st_mode),0o640)
  self.assertEqual((self.ex.workspace/"keep.txt").read_bytes(),b"keep\n")
 def test_failed_receipt_keeps_published_bytes_indeterminate(self):
  plan=self.freeze(lines=["keep published"])
  with patch.object(self.ex,"_result",side_effect=OSError("lost receipt")):
   with self.assertRaises(EffectIndeterminate):self.reg.execute(plan,"lost-lines-receipt")
  self.assertEqual((self.ex.workspace/self.path).read_bytes(),b"keep published\n")
  with self.assertRaises(ToolRejected):self.reg.execute(plan,"no-overwrite-retry")
 def test_small_scoped_replace_remains_available(self):
  self.create(lines=["left","right"]);obs=self.read().observation
  text=json.dumps(dict(tool="replace",arguments=dict(path=self.path,before="right",after="correct")))
  self.reg.execute(self.reg.freeze(text,observations=(obs,)),"small-edit")
  self.assertEqual(self.read().stdout,b"left\ncorrect\n")
