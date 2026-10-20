"""Host binds actual observed versions; no model checksum copying."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from branchwrite.execution import Executor,Grant,ToolRejected
from branchwrite.tool_registry import ToolRegistry,FileObservation
from branchwrite.records import decode
class ObservedSourceTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  src=self.root/'source';src.mkdir();(src/'a.py').write_bytes(b'old')
  self.executor=Executor.create(src,self.root/'world');self.registry=ToolRegistry(self.executor,Grant(('a.py',),False,read_paths=('a.py',)))
  self.sha=hashlib.sha256(b'old').hexdigest();self.observed=FileObservation(self.registry.world,'a.py',self.sha)
 def proposal(self,**extra):return json.dumps(dict(tool='replace',arguments=dict(path='a.py',before='old',after='new',**extra)))
 def plan(self,observations=None):return self.registry.freeze(self.proposal(),observations=(self.observed,) if observations is None else observations)
 def test_actual_observed_hash_is_frozen_without_model_copy(self):
  p=self.plan();row=decode(p.data);self.assertEqual(row[0],'bw.tool-plan.v2')
  self.assertEqual(row[4],dict(path='a.py',before='old',after='new',source_sha256=self.sha));self.assertEqual(row[7],self.observed.wire)
 def test_existing_file_without_visible_observation_is_not_authorized(self):
  with self.assertRaisesRegex(ToolRejected,'read'):self.plan(())
 def test_foreign_world_read_is_not_a_witness(self):
  foreign=FileObservation('0'*64,'a.py',self.sha)
  with self.assertRaisesRegex(ToolRejected,'read'):self.plan((foreign,))
 def test_latest_read_is_not_replaced_by_an_older_matching_hash(self):
  last=FileObservation(self.registry.world,'a.py',hashlib.sha256(b'later').hexdigest())
  with self.assertRaisesRegex(ToolRejected,'stale'):self.plan((self.observed,last))
 def test_source_change_after_plan_rejects_before_write(self):
  p=self.plan();target=self.executor.workspace/'a.py';target.write_bytes(b'later')
  with self.assertRaisesRegex(ToolRejected,'stale'):self.registry.execute(p,'stale')
  self.assertEqual(target.read_bytes(),b'later')
 def test_actual_edit_uses_bound_hash_and_preserves_original(self):
  result=self.registry.execute(self.plan(),'edit')
  self.assertEqual(result.disposition,'applied');self.assertEqual((self.executor.workspace/'a.py').read_bytes(),b'new')
  self.assertEqual(result.observation.sha256,hashlib.sha256(b'new').hexdigest());self.assertEqual((self.executor.source/'a.py').read_bytes(),b'old')
 def test_old_checksum_argument_is_explicitly_rejected(self):
  with self.assertRaisesRegex(ToolRejected,'unknown'):self.registry.freeze(self.proposal(source_sha256=self.sha),observations=(self.observed,))
 def test_model_schema_does_not_require_an_opaque_checksum(self):
  replace=next(v for v in self.registry.model_schema()['oneOf'] if v['properties']['tool']['enum']==['replace'])
  self.assertEqual(set(replace['properties']['arguments']['required']),{'path','before','after'})
 def test_corrupt_internal_bound_hash_is_rejected(self):
  from branchwrite.tool_registry import FrozenToolPlan
  from branchwrite.records import encode
  row=list(decode(self.plan().data));row[4]['source_sha256']='not-a-hash'
  with self.assertRaises(ToolRejected):self.registry.execute(FrozenToolPlan(encode(tuple(row))),'bad-bound')
  self.assertEqual((self.executor.workspace/'a.py').read_bytes(),b'old')
 def test_v1_plan_is_not_silently_reinterpreted(self):
  from branchwrite.tool_registry import FrozenToolPlan
  from branchwrite.records import encode
  row=list(decode(self.plan().data));row[0]='bw.tool-plan.v1'
  with self.assertRaises(ToolRejected):self.registry.execute(FrozenToolPlan(encode(tuple(row))),'old-plan')
  self.assertEqual((self.executor.workspace/'a.py').read_bytes(),b'old')
 def test_repeated_digest_read_preserves_latest_canonical_observation(self):
  from branchwrite.records import RuntimeLog
  from branchwrite.kernel import FrameKernel
  from branchwrite.interpreter import Interpreter,Value
  actions=[('read_file',dict(path='a.py')),('replace',dict(path='a.py',before='old',after='later')),
   ('read_file',dict(path='a.py')),('replace',dict(path='a.py',before='later',after='old')),
   ('read_file',dict(path='a.py')),('replace',dict(path='a.py',before='old',after='final'))]
  lines=['FLOW versions'];bindings={}
  for i,(tool,args) in enumerate(actions):
   name='request'+str(i);bindings[name]=Value('ToolProposal',json.dumps(dict(tool=tool,arguments=args)))
   lines+=['PLAN p'+str(i)+' from='+name+' against=world -> plan','ACT a'+str(i)+' plan=plan -> outcome'+str(i)]
  lines+=['END']
  with RuntimeLog(self.root/'ledger') as log:
   runtime=Interpreter(FrameKernel(log),self.registry);runtime.start('\n'.join(lines)+'\n',bindings);r=runtime.run()
   self.assertEqual(r.value['bindings']['outcome5'][1]['disposition'],'applied')
  self.assertEqual((self.executor.workspace/'a.py').read_bytes(),b'final')
if __name__=='__main__':unittest.main()
