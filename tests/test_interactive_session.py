"""Session plumbing with real Git/ledger/files; fixture driver is not GPU evidence."""
import json
from pathlib import Path
import shutil
import tempfile
import threading
import time
import unittest


class FixtureDriver:
    def __init__(self):
        self.calls=[];self.entered=threading.Event();self.release=threading.Event()
        self.release.set();self.fail_once=False
    def __call__(self,state,launch,connection,control,progress):
        self.calls.append((str(state),launch));self.entered.set()
        if not self.release.wait(10):raise RuntimeError('test release timeout')
        workspace=state/'world/workspace';workspace.mkdir(parents=True,exist_ok=True)
        source=Path(launch['config']['source'])
        for p in source.iterdir():
            if p.is_file() and p.name!='.git':shutil.copy2(p,workspace/p.name)
        readonly=launch['config']['verification'].get('read_only',False)
        if not readonly:(workspace/'index.html').write_text(launch['config']['bindings']['task']['value'])
        if self.fail_once:
            self.fail_once=False;raise RuntimeError('lost operation reply; retain original workflow')
        n=len(self.calls)
        context=dict(branch=launch['config']['cow']['branch'],tip=format(n,'064x'),root='a'*64,
            revision=n,model_contract_id='model',execution_profile_id='profile',mode='append_user')
        return dict(status='interrupted' if control() else 'finished',context=context,
            answer='Here is the result.',checks_passed=True,workspace=str(workspace))


class InteractiveSessionTests(unittest.TestCase):
    def setUp(self):
        from branchwrite.interactive_session import SessionService
        self.Service=SessionService;self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.project=self.root/'project';self.project.mkdir()
        (self.project/'keep.txt').write_text('untouched')
        self.state=self.root/'session';self.driver=FixtureDriver()
        self.connection=dict(endpoint_url='http://127.0.0.1:1',endpoint_pin='test',model_contract_id='model',execution_profile_id='profile',eos_tokens=[1])
        self.output=[];self.service=self.open();self.addCleanup(self.service.close)
    def open(self):
        service=self.Service(self.project,self.state,self.connection,runner=self.driver)
        service.start(self.output.append);return service
    def wait(self,predicate):
        limit=time.monotonic()+10
        while time.monotonic()<limit:
            if predicate():return
            time.sleep(.02)
        self.fail(str(self.service.snapshot))
    def finished(self,count):
        self.wait(lambda:len(self.service.snapshot.get('history',[]))>=count and not self.service.running and self.service.snapshot['history'][-1]['result'] is not None)
    def test_work_publishes_in_current_directory_and_followup_forks_saved_context(self):
        self.service.submit('Make a blue page',mode='work',kind='send');self.finished(1)
        first=self.service.snapshot['history'][0]['result']
        self.assertIn('blue',(self.project/'index.html').read_text())
        self.service.submit('Make the title larger',mode='work',kind='send');self.finished(2)
        launch=self.driver.calls[1][1]
        self.assertEqual(launch['fork']['snapshot'],first['context']['tip'])
        self.assertEqual(launch['fork']['source_branch'],first['context']['branch'])
        self.assertEqual((self.project/'keep.txt').read_text(),'untouched')
        self.assertTrue(first['file_commit']);self.assertIn('Here is the result.',self.output)
    def test_queued_followups_combine_without_stopping_active_work(self):
        self.driver.release.clear();self.service.submit('First',mode='work',kind='send')
        self.assertTrue(self.driver.entered.wait(5))
        self.service.submit('Make it blue',mode='work',kind='queue')
        self.service.submit('Also add a title',mode='work',kind='queue')
        self.driver.release.set();self.finished(2)
        history=self.service.snapshot['history']
        self.assertEqual(history[0]['result']['status'],'finished')
        self.assertEqual(history[1]['input']['message'],'Make it blue\n\nAlso add a title')
        self.assertEqual(len(self.driver.calls),2)
    def test_steering_interrupts_at_safe_boundary_then_uses_new_request(self):
        self.driver.release.clear();self.service.submit('First',mode='work',kind='send')
        self.assertTrue(self.driver.entered.wait(5))
        self.service.submit('Actually use green',mode='work',kind='steer')
        self.driver.release.set();self.finished(2)
        self.assertEqual(self.service.snapshot['history'][0]['result']['status'],'interrupted')
        self.assertIn('green',(self.project/'index.html').read_text())
    def test_plan_and_aside_do_not_publish_and_aside_does_not_move_current_context(self):
        self.service.submit('Build',mode='work',kind='send');self.finished(1)
        before=(self.project/'index.html').read_bytes();context=self.service.snapshot['current']['context']
        self.service.submit('Why blue?',mode='aside',kind='queue');self.finished(2)
        self.assertEqual(self.service.snapshot['current']['context'],context)
        self.assertEqual((self.project/'index.html').read_bytes(),before)
        self.assertTrue(self.driver.calls[-1][1]['config']['verification']['read_only'])
        self.service.submit('Plan next steps',mode='plan',kind='send');self.finished(3)
        self.assertEqual((self.project/'index.html').read_bytes(),before)
    def test_unknown_operation_remains_pending_and_recovery_uses_same_saved_launch(self):
        self.driver.fail_once=True;self.service.submit('Build',mode='work',kind='send')
        self.wait(lambda:self.service.snapshot.get('needs_recovery'))
        first=self.driver.calls[0]
        self.assertFalse((self.project/'index.html').exists())
        self.service.close();self.service=self.open();self.addCleanup(self.service.close)
        self.wait(lambda:self.service.snapshot.get('needs_recovery'))
        self.assertEqual(len(self.driver.calls),1,'restart must not silently retry an unresolved effect')
        self.service.submit('continue',mode='continue',kind='queue');self.finished(1)
        self.assertEqual(self.driver.calls[1],first)
        self.assertEqual(len(self.service.snapshot['history']),1)

    def test_input_worktree_preserves_private_file_modes(self):
        import stat
        (self.project/'keep.txt').chmod(0o600)
        self.service.submit('Build',mode='work',kind='send');self.finished(1)
        self.assertEqual(stat.S_IMODE((self.project/'keep.txt').stat().st_mode),0o600)
    def test_explicit_continue_unpauses_a_stopped_worker(self):
        self.driver.release.clear();self.service.submit('Build',mode='work',kind='send')
        self.assertTrue(self.driver.entered.wait(5));self.service.stop();self.driver.release.set()
        self.finished(1)
        self.assertEqual(self.service.snapshot['history'][0]['result']['status'],'interrupted')
        self.service.submit('continue',mode='continue',kind='queue');self.finished(2)
        self.assertEqual(self.driver.calls[0][0],self.driver.calls[1][0])
        self.assertEqual(self.service.snapshot['history'][1]['result']['status'],'finished')

    def test_continue_without_a_paused_turn_is_rejected_before_admission(self):
        self.wait(lambda:self.service.snapshot['status']=='ready')
        with self.assertRaisesRegex(ValueError,'paused'):
            self.service.submit('continue',mode='continue',kind='queue')
        self.assertEqual(self.service.inbox.rows(),[])
        self.assertEqual(self.service.snapshot['history'],[])
        self.service.submit('Build',mode='work',kind='send');self.finished(1)
        with self.assertRaisesRegex(ValueError,'paused'):
            self.service.submit('continue',mode='continue',kind='queue')
        self.assertEqual(self.service.inbox.rows(),[])

    def test_continue_while_working_does_not_queue_duplicate_resume(self):
        self.driver.release.clear();self.service.submit('Build',mode='work',kind='send')
        self.assertTrue(self.driver.entered.wait(5))
        try:
            with self.assertRaisesRegex(ValueError,'already working'):
                self.service.submit('continue',mode='continue',kind='queue')
            self.assertEqual(self.service.inbox.rows(),[])
        finally:self.driver.release.set()
        self.finished(1)

    def test_failed_worker_open_requires_reopening_not_an_unhandled_queue(self):
        self.wait(lambda:self.service.snapshot['status']=='ready')
        self.service.close()
        (self.state/'files/project.json').write_text('{broken')
        self.service=self.open();self.addCleanup(self.service.close)
        self.wait(lambda:self.service.snapshot.get('needs_recovery'))
        with self.assertRaisesRegex(ValueError,'reopen'):
            self.service.submit('continue',mode='continue',kind='queue')
        self.assertEqual(self.service.inbox.rows(),[])

    def test_edit_first_request_uses_its_preceding_files_and_context(self):
        self.service.submit('Make blue',mode='work',kind='send');self.finished(1)
        first=self.service.snapshot['history'][0]
        self.service.submit('Make larger',mode='work',kind='send');self.finished(2)
        self.service.submit('1 Make green instead',mode='edit',kind='queue');self.finished(3)
        launch=self.driver.calls[-1][1]
        self.assertIsNone(launch['fork'],'first request starts before any model context')
        self.assertFalse((Path(launch['config']['source'])/'index.html').exists())
        self.assertIn('Make green instead',(self.project/'index.html').read_text())
        self.assertEqual(self.service.snapshot['history'][-1]['result']['before'],first['result']['before'])
        self.assertEqual(self.service.snapshot['history'][0],first,'old version remains selectable')

    def test_explore_old_context_with_current_files_and_switch_back_without_inference(self):
        self.service.submit('Make blue',mode='work',kind='send');self.finished(1)
        first=self.service.snapshot['history'][0]['result']
        self.service.submit('Make larger',mode='work',kind='send');self.finished(2)
        second=self.service.snapshot['history'][1]['result'];original=(self.project/'index.html').read_bytes()
        (self.project/'notes.txt').write_text('new user notes')
        self.service.submit('1 Try green independently',mode='explore',kind='queue');self.finished(3)
        launch=self.driver.calls[-1][1];alternative=self.service.snapshot['current']
        self.assertEqual(launch['fork']['snapshot'],first['context']['tip'])
        self.assertEqual((Path(launch['config']['source'])/'index.html').read_bytes(),original)
        self.assertEqual((self.project/'index.html').read_bytes(),original)
        self.assertNotEqual(alternative['workdir'],str(self.project))
        self.assertIn('Try green', (Path(alternative['workdir'])/'index.html').read_text())
        self.assertEqual((Path(alternative['workdir'])/'notes.txt').read_text(),'new user notes')
        self.service.submit('2',mode='select',kind='queue');self.finished(4)
        self.assertEqual(len(self.driver.calls),3,'switch must not invoke the model')
        self.assertEqual(self.service.snapshot['current']['context'],second['context'])
        self.assertEqual(self.service.snapshot['current']['workdir'],str(self.project))
        self.assertEqual((self.project/'notes.txt').read_text(),'new user notes')
        self.assertEqual((self.project/'index.html').read_bytes(),original)

    def test_switch_restores_matching_files_then_followup_uses_that_exact_tip(self):
        self.service.submit('Make blue',mode='work',kind='send');self.finished(1)
        first=self.service.snapshot['history'][0]['result'];blue=(self.project/'index.html').read_bytes()
        self.service.submit('Make green',mode='work',kind='send');self.finished(2)
        self.service.submit('1',mode='select',kind='queue');self.finished(3)
        self.assertEqual((self.project/'index.html').read_bytes(),blue)
        self.assertEqual(self.service.snapshot['current']['context'],first['context'])
        self.assertEqual(len(self.driver.calls),2)
        self.service.submit('Add a button',mode='work',kind='send');self.finished(4)
        self.assertEqual(self.driver.calls[-1][1]['fork']['snapshot'],first['context']['tip'])
        self.assertEqual((Path(self.driver.calls[-1][1]['config']['source'])/'index.html').read_bytes(),blue)

    def test_invalid_control_target_rejects_before_admission(self):
        self.wait(lambda:self.service.snapshot['status']=='ready')
        with self.assertRaisesRegex(ValueError,'saved turn'):
            self.service.submit('99 Make blue',mode='edit',kind='queue')
        self.assertEqual(self.service.inbox.rows(),[])
        self.assertFalse(self.service.snapshot['needs_recovery'])

    def test_branch_controls_wait_for_settled_work(self):
        self.driver.release.clear();self.service.submit('Make blue',mode='work',kind='send')
        self.assertTrue(self.driver.entered.wait(5))
        try:
            with self.assertRaisesRegex(ValueError,'Stop|settle'):
                self.service.submit('last Change it',mode='edit',kind='queue')
            self.assertEqual(self.service.inbox.rows(),[])
        finally:self.driver.release.set()
        self.finished(1)

    def test_switch_conflict_preserves_user_edit_and_original_control_id(self):
        self.service.submit('Make blue',mode='work',kind='send');self.finished(1)
        self.service.submit('Make green',mode='work',kind='send');self.finished(2)
        green=(self.project/'index.html').read_bytes()
        (self.project/'index.html').write_text('my manual edit')
        self.service.submit('1',mode='select',kind='queue')
        self.wait(lambda:self.service.snapshot['needs_recovery'])
        self.assertEqual((self.project/'index.html').read_text(),'my manual edit')
        pending=self.service.snapshot['history'][-1]['id']
        self.service.close();self.service=self.open();self.addCleanup(self.service.close)
        self.wait(lambda:self.service.snapshot['needs_recovery'])
        (self.project/'index.html').write_bytes(green)
        self.service.submit('continue',mode='continue',kind='queue');self.finished(3)
        self.assertEqual(self.service.snapshot['history'][-1]['id'],pending)
        self.assertEqual(len(self.driver.calls),2)
        self.assertIn('Make blue',(self.project/'index.html').read_text())

    def test_lost_alternative_publication_reply_recovers_without_model_rerun(self):
        from unittest.mock import patch
        from branchwrite.workspace_versions import WorkspaceVersions
        self.service.submit('Make blue',mode='work',kind='send');self.finished(1)
        original=(self.project/'index.html').read_bytes();publish=WorkspaceVersions.publish
        def lost_reply(instance,*args,**kwargs):
            result=publish(instance,*args,**kwargs)
            raise OSError('lost publication reply')
        with patch.object(WorkspaceVersions,'publish',lost_reply):
            self.service.submit('last Try green',mode='explore',kind='queue')
            self.wait(lambda:self.service.snapshot['needs_recovery'])
        calls=len(self.driver.calls)
        self.service.close();self.service=self.open();self.addCleanup(self.service.close)
        self.wait(lambda:self.service.snapshot['needs_recovery'])
        self.service.submit('continue',mode='continue',kind='queue');self.finished(2)
        self.assertEqual(len(self.driver.calls),calls)
        self.assertEqual((self.project/'index.html').read_bytes(),original)
        self.assertIn('Try green',(Path(self.service.snapshot['current']['workdir'])/'index.html').read_text())

    def test_edit_first_request_reuses_the_recorded_prepared_model_prefix(self):
        from branchwrite.records import RuntimeLog, encode
        from branchwrite.kernel import FrameKernel, ResultContract
        def with_saved_prefix(state,launch,connection,control,progress):
            result=self.driver(state,launch,connection,control,progress)
            with RuntimeLog(state/'ledger') as log:
                kernel=FrameKernel(log)
                kernel.create_root('program','attempt',log.put_artifact(b'fixture'),
                    log.put_artifact(encode(dict(bindings={'current':('COWSource',dict(
                        head=dict(name=launch['config']['cow']['branch'],tip='9'*64,root='9'*64,revision=0),mode='ask'))}))),
                    ResultContract('ProgramResult','record'))
            return result
        self.service.runner=with_saved_prefix
        self.service.submit('Make blue',mode='work',kind='send');self.finished(1)
        self.service.submit('1 Make green',mode='edit',kind='queue');self.finished(2)
        launch=self.driver.calls[-1][1]
        self.assertEqual(launch['fork']['snapshot'],'9'*64)
        self.assertEqual(launch['config']['cow']['mode'],'ask')
        self.assertNotIn('bootstrap',launch['config']['cow'])
        self.assertFalse((Path(launch['config']['source'])/'index.html').exists())

    def test_selected_sampler_applies_only_to_new_admissions(self):
        self.service.close()
        self.service=self.Service(self.project,self.state,self.connection,runner=self.driver,sampler='min-p')
        self.service.start(self.output.append);self.addCleanup(self.service.close)
        self.service.submit('Build',mode='work',kind='send');self.finished(1)
        profile=self.driver.calls[0][1]['config']['profiles']['control']
        self.assertEqual(profile['settings']['temperature'],.70)
        self.assertEqual(profile['settings']['min_p'],.05)
        self.assertEqual(profile['settings']['dry_multiplier'],0.0)
    def test_new_sampler_does_not_rewrite_an_unresolved_saved_launch(self):
        self.service.close()
        self.service=self.Service(self.project,self.state,self.connection,runner=self.driver,sampler='min-p')
        self.service.start(self.output.append);self.addCleanup(self.service.close)
        self.driver.fail_once=True;self.service.submit('Build',mode='work',kind='send')
        self.wait(lambda:self.service.snapshot.get('needs_recovery'));first=self.driver.calls[0]
        self.service.close()
        self.service=self.Service(self.project,self.state,self.connection,runner=self.driver,sampler='dry-min-p')
        self.service.start(self.output.append);self.addCleanup(self.service.close)
        self.wait(lambda:self.service.snapshot.get('needs_recovery'))
        self.service.submit('continue',mode='continue',kind='queue');self.finished(1)
        self.assertEqual(self.driver.calls[1],first)
        self.assertEqual(self.driver.calls[1][1]['config']['profiles']['control']['settings']['dry_multiplier'],0.0)
    def test_unknown_sampler_fails_before_opening_workflow(self):
        with self.assertRaises(ValueError):self.Service(self.project,self.state,self.connection,sampler='invented')
