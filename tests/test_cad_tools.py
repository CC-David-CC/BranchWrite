"""CAD uses ordinary host plans, artifacts and current-inventory verification."""
import json,tempfile,unittest
from pathlib import Path
from branchwrite.execution import Executor,Grant,ToolRejected
from branchwrite.tool_registry import ToolRegistry
from branchwrite.cad_execution import CadRuntime
from branchwrite.cad_tools import CadCapability,CadPolicy
from branchwrite.records import RuntimeLog,Artifact,encode
from test_cad_evaluation import LIBS
from test_cad_execution import RUNTIME,SOURCE
from test_cad_geometry import spec
class CadToolTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.cap=CadCapability(CadRuntime(RUNTIME,timeout=30,osmesa=LIBS),spec())
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);root=Path(self.tmp.name)
  source=root/'source';source.mkdir();(source/'model.py').write_bytes(SOURCE)
  self.ex=Executor.create(source,root/'world');self.grant=Grant((),False,project_files=True)
  self.registry=ToolRegistry(self.ex,self.grant,cad=self.cap);self.log=RuntimeLog(root/'ledger');self.addCleanup(self.log.close)
 def inspect(self):
  plan=self.registry.freeze(json.dumps(dict(tool='inspect_cad',arguments=dict(path='model.py'))))
  out=self.registry.execute(plan,'cad-check');value,_=out.publish(self.log)
  ref=self.log.put_artifact(plan.data);res=self.log.put_artifact(encode(('ToolOutcome',None,value)))
  frame=dict(id='actual-check',state='Closed',inputs=(ref.sha256,ref.size_bytes),result=(res.sha256,res.size_bytes),dispatch=('cad-check',None))
  return out,frame,value
 def test_tool_builds_checks_renders_and_roots_exact_export(self):
  out,frame,value=self.inspect();self.assertEqual(out.disposition,'cad_checked');self.assertEqual(out.exit_code,0)
  self.assertIsNotNone(value['image']);self.assertTrue(out.metadata['geometry']['status']=='PASS')
  self.assertTrue(CadPolicy.admit({'schema':1,'cad':True},self.registry).verify(self.registry,self.log,[(frame,value)])['status']=='pass')
  self.assertEqual(len(value['details']['asset_manifest']),8)
 def test_current_inventory_required_after_any_edit(self):
  _,frame,value=self.inspect();(self.ex.workspace/'model.py').write_bytes(SOURCE+b'\n# later edit\n')
  self.assertEqual(CadPolicy.admit({'schema':1,'cad':True},self.registry).verify(self.registry,self.log,[(frame,value)])['status'],'fail')
 def test_without_host_capability_cad_tool_is_absent(self):
  r=ToolRegistry(self.ex,self.grant)
  with self.assertRaises(ToolRejected):r.freeze(json.dumps(dict(tool='inspect_cad',arguments=dict(path='model.py'))))
 def test_changed_source_after_plan_is_rejected_before_build(self):
  plan=self.registry.freeze(json.dumps(dict(tool='inspect_cad',arguments=dict(path='model.py'))))
  (self.ex.workspace/'model.py').write_bytes(SOURCE+b'# change')
  with self.assertRaisesRegex(ToolRejected,'stale'):self.registry.execute(plan,'stale-cad')
 def test_model_cannot_change_requirements(self):
  with self.assertRaises(ToolRejected):self.registry.freeze(json.dumps(dict(tool='inspect_cad',arguments=dict(path='model.py',width_x=90))))

 def test_later_failed_attempt_supersedes_old_pass(self):
  from copy import deepcopy
  _,frame,value=self.inspect()
  failed=deepcopy(value);failed['disposition']='cad_failed';failed['exit_code']=1
  result=self.log.put_artifact(encode(('ToolOutcome',None,failed)))
  later=dict(frame,id='later-failed',result=(result.sha256,result.size_bytes))
  self.assertEqual(CadPolicy.admit({'schema':1,'cad':True},self.registry).verify(self.registry,self.log,[(frame,value),(later,failed)])['status'],'fail')

 def test_readonly_policy_rejects_enabled_cad_execution(self):
  from branchwrite.verification import ReadOnlyPolicy
  r=ToolRegistry(self.ex,Grant((),False,read_paths=('model.py',)),cad=self.cap)
  with self.assertRaises(ValueError):ReadOnlyPolicy.admit(dict(schema=1,read_only=True),r)
