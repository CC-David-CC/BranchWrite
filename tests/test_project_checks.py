"""Model-selected checks need actual, current, retired command evidence."""
import json,tempfile,unittest
from pathlib import Path
from branchwrite.execution import Executor,Grant
from branchwrite.terminal import ShellConfig
from branchwrite.tool_registry import ToolRegistry
from branchwrite.kernel import FrameKernel
from branchwrite.records import RuntimeLog
from branchwrite.interpreter import Interpreter,Value

class ProjectChecksTests(unittest.TestCase):
    def run_checks(self,checks,*,mutate=False):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);source=base/'source';source.mkdir();(source/'marker').write_text('good')
            executor=Executor.create(source,base/'world',shell=ShellConfig(timeout=2),project_input=True)
            registry=ToolRegistry(executor,Grant((),False,allow_shell=True,project_files=True))
            with RuntimeLog(base/'ledger') as log:
                kernel=FrameKernel(log)
                runtime=Interpreter(kernel,registry,verification=dict(schema=1,selected_checks=True))
                text='FLOW project\n';bindings={}
                for i,(name,command) in enumerate(checks):
                    label='c'+str(i)
                    bindings[label]=Value('ToolProposal',json.dumps(dict(tool='run_check',arguments=dict(name=name,command=command))))
                    text+='PLAN p'+str(i)+' from='+label+' against=world -> plan\nACT a'+str(i)+' plan=plan -> outcome\n'
                bindings['finish']=Value('ToolProposal',json.dumps(dict(tool='finish',arguments=dict(answer='done'))))
                text+='PLAN final from=finish against=world -> plan\nACT done plan=plan -> outcome\nVERIFY verify input=outcome contract=project-checks-and-finish -> verified\nEND\n'
                runtime.start(text,bindings)
                if mutate:
                    while kernel.frame('program')['pc']<2*len(checks) or kernel.frame('program')['state']=='Waiting':runtime.step()
                    (executor.workspace/'marker').write_text('changed after check')
                return runtime.run().value['verified']

    def test_finish_without_a_check_is_not_verified(self):self.assertFalse(self.run_checks([]))
    def test_actual_check_of_current_files_can_pass(self):
        self.assertTrue(self.run_checks([('content',"test $(cat marker) = good")]))
    def test_nonzero_check_is_not_verified(self):self.assertFalse(self.run_checks([('content','exit 4')]))
    def test_latest_failure_overrides_an_earlier_pass(self):
        self.assertFalse(self.run_checks([('content','test -f marker'),('content','exit 4')]))
    def test_repaired_named_check_can_replace_a_broken_command(self):
        self.assertTrue(self.run_checks([('content','exit 4'),('content','test -f marker')]))
    def test_different_check_cannot_hide_a_failed_named_check(self):
        self.assertFalse(self.run_checks([('first','exit 4'),('second','test -f marker')]))
    def test_changes_require_checks_to_run_again(self):
        self.assertFalse(self.run_checks([('content','test -f marker')],mutate=True))
    def test_plain_shell_observation_is_not_a_project_check(self):
        from branchwrite.verification import ProjectChecksPolicy
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);source=p/'source';source.mkdir()
            registry=ToolRegistry(Executor.create(source,p/'world',shell=ShellConfig(timeout=2)),Grant((),False,allow_shell=True,project_files=True))
            policy=ProjectChecksPolicy.admit(dict(schema=1,selected_checks=True),registry)
            with RuntimeLog(p/'ledger') as log:self.assertEqual(policy.verify(registry,log,())['status'],'fail')

if __name__=='__main__':unittest.main()
