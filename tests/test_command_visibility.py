"""Real command outcomes are visible only after the parent resumes."""
from pathlib import Path
import tempfile,unittest,json
from branchwrite.execution import Executor,Grant
from branchwrite.terminal import ShellConfig
from branchwrite.tool_registry import ToolRegistry
from branchwrite.records import RuntimeLog
from branchwrite.kernel import FrameKernel
from branchwrite.interpreter import Interpreter,Value
from branchwrite.tool_dispatch import tool_call,dispatch_tool
class VisibilityTests(unittest.TestCase):
 def test_closed_command_is_not_available_until_parent_resumes(self):
  with tempfile.TemporaryDirectory() as td:
   b=Path(td);s=b/'source';s.mkdir()
   registry=ToolRegistry(Executor.create(s,b/'world',shell=ShellConfig(timeout=1)),Grant((),False,allow_shell=True))
   with RuntimeLog(b/'ledger') as log:
    kernel=FrameKernel(log)
    runtime=Interpreter(kernel,registry,verification=dict(schema=1,commands=[dict(command='printf witnessed',disposition='exited',exit_code=0)]))
    program='FLOW task\nPLAN p from=finish against=world -> plan\nACT f plan=plan -> outcome\nVERIFY v input=outcome contract=command-evidence-and-finish -> verified\nEND\n'
    runtime.start(program,dict(finish=Value('ToolProposal',json.dumps(dict(tool='finish',arguments=dict(answer='done'))))))
    plan=registry.freeze(json.dumps(dict(tool='run_shell',arguments=dict(command='printf witnessed'))))
    call=tool_call(kernel,registry,child_id='unjoined-command',attempt_id='attempt-command',slot='result',plan=plan)
    kernel.spawn('program',expected_epoch=0,calls=(call,),next_pc=1)
    dispatch_tool(kernel,registry,'unjoined-command')
    parent=kernel.frame('program');self.assertEqual(parent['state'],'Waiting')
    before=runtime._verification(dict(requested_finish=True),policy='command-evidence-and-finish',frame=parent)
    self.assertEqual(before['status'],'fail')
    kernel.resume('program',parent['epoch'])
    after=runtime._verification(dict(requested_finish=True),policy='command-evidence-and-finish',frame=kernel.frame('program'))
    self.assertEqual(after['status'],'pass')
