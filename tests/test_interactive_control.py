"""Interactive control pauses the existing interpreter without losing effects."""
import json,tempfile,unittest
from pathlib import Path
from branchwrite.execution import Executor,Grant
from branchwrite.tool_registry import ToolRegistry
from branchwrite.kernel import FrameKernel
from branchwrite.records import RuntimeLog
from branchwrite.interpreter import Interpreter,Value

class InteractiveControlTests(unittest.TestCase):
    def test_interrupt_before_tool_then_resume_executes_once(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); source=p/'source';source.mkdir()
            executor=Executor.create(source,p/'world')
            registry=ToolRegistry(executor,Grant((),False,create_paths=('new.txt',)))
            with RuntimeLog(p/'ledger') as log:
                kernel=FrameKernel(log);runtime=Interpreter(kernel,registry)
                program='FLOW task\nPLAN p from=proposal against=world -> plan\nACT a plan=plan -> outcome\nEND\n'
                runtime.start(program,{'proposal':Value('ToolProposal',json.dumps({'tool':'create_file','arguments':{'path':'new.txt','content':'once'}}))})
                paused=runtime.run(control=lambda:True)
                self.assertEqual(paused.status,'interrupted')
                self.assertFalse((executor.workspace/'new.txt').exists())
                self.assertEqual(log.event_count,1)
                completed=runtime.run(control=lambda:False)
                self.assertEqual(completed.status,'complete')
                self.assertEqual((executor.workspace/'new.txt').read_text(),'once')
                before=log.event_count
                self.assertEqual(runtime.run(control=lambda:False).status,'complete')
                self.assertEqual(log.event_count,before)
    def test_pause_after_consumed_effect_keeps_real_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);source=p/'source';source.mkdir()
            executor=Executor.create(source,p/'world')
            registry=ToolRegistry(executor,Grant((),False,create_paths=('new.txt',)))
            with RuntimeLog(p/'ledger') as log:
                kernel=FrameKernel(log);runtime=Interpreter(kernel,registry)
                runtime.start('FLOW task\nPLAN p from=proposal against=world -> plan\nACT a plan=plan -> outcome\nEND\n',
                    {'proposal':Value('ToolProposal',json.dumps({'tool':'create_file','arguments':{'path':'new.txt','content':'once'}}))})
                result=runtime.run(control=lambda:(executor.workspace/'new.txt').exists())
                self.assertEqual(result.status,'interrupted')
                tools=[f for f in kernel.frames() if f['contract']==('ToolOutcome','record')]
                self.assertEqual(len(tools),1);self.assertEqual(tools[0]['state'],'Closed')
                before=tools[0]['result']
                runtime.run(control=lambda:False)
                self.assertEqual(kernel.frame(tools[0]['id'])['result'],before)
