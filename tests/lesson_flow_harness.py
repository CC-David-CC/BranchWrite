"""Controlled failed proposal + host correction through real BW tool boundaries.

This is fault injection, not evidence of a spontaneous model error. Uses the
production ledger, grants, preimages and isolated executor; never trains on tests.
"""
from pathlib import Path
import hashlib
import json
from branchwrite.coding_cli import build_launch,save_launch
from branchwrite.execution import Executor,Grant
from branchwrite.tool_registry import ToolRegistry
from branchwrite.terminal import ShellConfig
from branchwrite.records import RuntimeLog,encode
from branchwrite.kernel import FrameKernel,ResultContract,CallSpec

def task(root,connection,*,corrected,factor=2,name='double',include_failed_check=False):
    root=Path(root);project=root/'project';project.mkdir(parents=True,mode=0o700)
    (project/'tests').mkdir();(project/'tests/__init__.py').write_text('')
    (project/'app.py').write_text('def '+name+'(n):\n    return n\n')
    # Independent deterministic checks stay out of teaching text and completion.
    (project/'tests/test_values.py').write_text('import unittest, random\nfrom app import '+name+'\nclass Values(unittest.TestCase):\n def test_values(self):\n  rng=random.Random(9217)\n  for n in [-1000000,-1,0,1,1000000]+[rng.randrange(-500,500) for _ in range(23)]:\n   self.assertEqual('+name+'(n),n*'+str(factor)+')\n')
    command='python3 -B -m unittest discover -s tests'
    state=root/'state';launch=build_launch(project,'Repair '+name,connection,branch='controlled-task',
        read_paths=['app.py','tests/test_values.py','tests/__init__.py'],edit_paths=['app.py'],test_commands=[command])
    save_launch(state,launch)
    ex=Executor.create(project,state/'world',shell=ShellConfig(timeout=30));registry=ToolRegistry(ex,Grant(**launch['config']['grant']))
    with RuntimeLog(state/'ledger') as log:
        kernel=FrameKernel(log);definition=log.put_artifact(b'controlled-lesson-harness-v1')
        config_hash=hashlib.sha256(json.dumps(launch['config'],sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
        inputs=log.put_artifact(encode(dict(bindings={'host-config-sha256':('Text',config_hash)})))
        kernel.create_root('program','controlled-attempt',definition,inputs,ResultContract('ProgramResult','record'))
        epoch=0;observations=[]
        def act(tool,arguments):
            nonlocal epoch
            plan=registry.freeze(json.dumps(dict(tool=tool,arguments=arguments)),observations=tuple(observations))
            ref=log.put_artifact(plan.data);child='step-'+str(epoch)
            kernel.spawn('program',expected_epoch=epoch,calls=(CallSpec(child,'attempt-'+str(epoch),'result','ACT',definition,ref,ResultContract('ToolOutcome','record')),),next_pc=epoch+1)
            kernel.dispatch(child,'op-'+str(epoch),ref)
            result=registry.execute(plan,'op-'+str(epoch));value,refs=result.publish(log)
            kernel.record_result(child,'op-'+str(epoch),value,provenance=refs)
            epoch+=1;kernel.resume('program',epoch)
            if result.observation:observations.append(result.observation)
            return result
        if corrected:
            if include_failed_check:
                failed=act('run_shell',dict(command=command))
                assert failed.disposition=='exited' and failed.exit_code!=0
            act('read_file',dict(path='app.py'))
            act('replace',dict(path='app.py',before='return n',after='return '+str(factor)+'*n'))
        checked=act('run_shell',dict(command=command))
        if checked.disposition!='exited':raise AssertionError('Harness infrastructure failed: '+checked.disposition)
        passed=checked.exit_code==0
        assert passed is corrected,'Controlled expected task outcome differs from actual isolated checks'
        kernel.finish('program',dict(verified=passed))
    return state
