"""Normal startup needs a task, not advance knowledge of filenames or tests."""
import tempfile,unittest,json
from pathlib import Path
from unittest.mock import patch
from branchwrite import guided_cli,coding_cli
CONNECTION=dict(endpoint_url='http://127.0.0.1:1',endpoint_pin='test',model_contract_id='m',execution_profile_id='p',eos_tokens=[256])
class GuidedProjectStartTests(unittest.TestCase):
    def test_task_alone_admits_whole_project_and_model_selected_checks(self):
        with tempfile.TemporaryDirectory() as td:
            home=Path(td)/'home';home.mkdir();project=Path(td)/'project';project.mkdir()
            config=home/'.config/branchwrite';config.mkdir(parents=True)
            (config/'connection.json').write_text(json.dumps(CONNECTION))
            prompts=[]
            def answer(prompt):
                prompts.append(prompt)
                if prompt=='What would you like changed? ':return 'Create a mobile-friendly page.'
                raise AssertionError('Unnecessary setup question: '+prompt)
            with patch('branchwrite.guided_cli._run_and_report',return_value=0) as run:
                code=guided_cli.run(cwd=project,home=home,environ={'BW_COW_API_KEY':'test'},input_fn=answer,output_fn=lambda _:None)
            self.assertEqual(code,0);args=run.call_args.args[0]
            self.assertTrue(args.project_files)
            self.assertEqual(args.test_command,[])
            self.assertEqual(len(prompts),1)
    def test_project_launch_has_no_filename_or_check_list(self):
        with tempfile.TemporaryDirectory() as td:
            launch=coding_cli.build_launch(td,'Make a page',CONNECTION,branch='new-project',project_files=True)
            self.assertTrue(launch['config']['grant']['project_files'])
            self.assertEqual(launch['config']['verification'],dict(schema=1,selected_checks=True))
            self.assertIn('project-checks-and-finish',launch['program'])
            coding_cli._validate(launch)
            state=Path(td).parent/(Path(td).name+'-state')
            try:
                coding_cli.save_launch(state,launch)
                self.assertEqual(coding_cli.read_launch(state),launch)
            finally:
                import shutil
                shutil.rmtree(state,ignore_errors=True)
    def test_review_error_does_not_claim_completed_delivery(self):
        with patch('branchwrite.coding_review.inspect_changes',side_effect=ValueError('review failed')):
            result=guided_cli._verified_summary(0,{'verified':True},project=Path('/tmp/project'),state=Path('/tmp/state'),branch='x',runs_dir=Path('/tmp'),input_fn=lambda _:None,output_fn=lambda _:None)
        self.assertEqual(result,2)
    def test_fixed_scope_launch_still_requires_explicit_checks(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError,'explicit verification'):
                coding_cli.build_launch(td,'task',CONNECTION,branch='fixed')
if __name__=='__main__':unittest.main()
