"""Review and execution must use the same resumed-path visibility rule."""
import tempfile,unittest
from pathlib import Path
from branchwrite.records import RuntimeLog,encode
from branchwrite.kernel import FrameKernel,ResultContract,CallSpec
class VisibleResultTests(unittest.TestCase):
 def test_unresumed_children_are_not_visible_and_resumed_children_are(self):
  with tempfile.TemporaryDirectory() as t,RuntimeLog(Path(t)/'ledger') as log:
   k=FrameKernel(log);a=log.put_artifact(b'def');i=log.put_artifact(encode({}))
   k.create_root('program','attempt',a,i,ResultContract('ProgramResult','record'))
   c=ResultContract('ToolOutcome','record')
   k.spawn('program',expected_epoch=0,calls=(CallSpec('child','a1','slot','ACT',a,i,c),),next_pc=1)
   k.dispatch('child','op',i);k.record_result('child','op',{'tool':'read_file'})
   self.assertEqual(k.visible_results(k.frame('program'),c.wire),())
   k.resume('program',1)
   got=k.visible_results(k.frame('program'),c.wire)
   self.assertEqual([(f['id'],v) for f,v in got],[('child',{'tool':'read_file'})])
 def test_a_later_unjoined_sibling_does_not_replace_prior_observation(self):
  with tempfile.TemporaryDirectory() as t,RuntimeLog(Path(t)/'ledger') as log:
   k=FrameKernel(log);a=log.put_artifact(b'def');i=log.put_artifact(encode({}))
   k.create_root('program','attempt',a,i,ResultContract('ProgramResult','record'))
   c=ResultContract('ToolOutcome','record')
   for idx in [1,2]:
    child='child'+str(idx);op='op'+str(idx)
    k.spawn('program',expected_epoch=idx-1,calls=(CallSpec(child,'a'+str(idx),'slot','ACT',a,i,c),),next_pc=idx)
    k.dispatch(child,op,i);k.record_result(child,op,{'value':idx})
    if idx==1:k.resume('program',idx)
   got=k.visible_results(k.frame('program'),c.wire)
   self.assertEqual([v for _,v in got],[{'value':1}])
