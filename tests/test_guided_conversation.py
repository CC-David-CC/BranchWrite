"""Conversation startup uses real COW HTTP; the CPU model is a deterministic fixture."""
import contextlib
import io
import json
import os
from collections import defaultdict
from pathlib import Path
import unittest
from unittest.mock import patch
import test_cow_client_flow as fixture
from branchwrite import guided_cli, chat_cli

class GuidedConversationTests(unittest.TestCase):
    def setUp(self):
        self.case=fixture.CowClientFlowTests();self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.root=Path(self.case.temp.name)
        self.home=self.root/'home';self.home.mkdir()
        self.project=self.root/'project';self.project.mkdir()
        (self.project/'keep.txt').write_text('original\n')
        self.connection=self.root/'connection.json'
        self.connection.write_text(json.dumps(dict(endpoint_url=self.case.base_url,
            endpoint_pin='flow-model-free',model_contract_id='flow-model',
            execution_profile_id='flow-profile',eos_tokens=[299])))
        self.env=dict(BW_COW_CONNECTION=str(self.connection),BW_COW_API_KEY='cpu-flow-secret',
            XDG_STATE_HOME=str(self.home/'state'))
        self.model=next(iter(self.case.models.values()))
        self.model.plans=defaultdict(lambda:(257,299))
        self.addCleanup(self.model.gate.set)

    def run_chat(self, messages, *, coding_error=None, **options):
        answers=iter(messages);self.prompts=[];output=io.StringIO()
        def answer(prompt):
            self.prompts.append(prompt);return next(answers)
        with patch('branchwrite.guided_cli._run_and_report',return_value=0,side_effect=coding_error) as coding, \
             contextlib.redirect_stdout(output),contextlib.redirect_stderr(output):
            code=guided_cli.run(cwd=self.project,home=self.home,environ=self.env,
                input_fn=answer,output_fn=print,**options)
        return code,output.getvalue(),coding

    def chat_state(self):
        files=list((self.home/'state').rglob('chat.json'))
        self.assertEqual(len(files),1)
        return files[0].parent

    def test_talk_keeps_two_turns_without_starting_coding_or_reading_project(self):
        code,out,coding=self.run_chat(['Explain blue headings.','What about phones?','/exit'],mode='chat')
        self.assertEqual(code,0,out);coding.assert_not_called()
        state=self.chat_state();chat=chat_cli._read(state)
        self.assertEqual(chat['turn_count'],2);self.assertIsNone(chat['pending'])
        client=self.case._client('http','inspect-talk')
        text='\n'.join(row.get('text','') for row in client.history(chat['branch']).messages)
        self.assertIn('Explain blue headings.',text);self.assertIn('What about phones?',text)
        self.assertNotIn('original',text)
        self.assertEqual((self.project/'keep.txt').read_text(),'original\n')
        self.assertEqual(list(self.project.iterdir()),[self.project/'keep.txt'])
        self.assertFalse(list(state.rglob('coding-launch.json')))
        self.assertNotIn('cpu-flow-secret',(state/'chat.json').read_text())
        self.assertIn('branchwrite talk --state',out)

    def test_code_switch_pins_the_completed_conversation_in_a_new_workflow(self):
        code,out,coding=self.run_chat(['Keep the title blue.','/code Create index.html'],mode='chat')
        self.assertEqual(code,0,out);coding.assert_called_once()
        chat=chat_cli._read(self.chat_state());args=coding.call_args.args[0]
        self.assertEqual(args.task,'Create index.html')
        self.assertEqual(args.from_branch,chat['branch']);self.assertEqual(args.from_snapshot,chat['head']['tip'])
        self.assertNotEqual(args.branch,chat['branch']);self.assertTrue(args.project_files)
        self.assertNotEqual(args.state,self.chat_state())
        self.assertEqual(self.case.coordinator.store.head(chat['branch']).tip,chat['head']['tip'])

    def test_open_and_exit_makes_no_namespace_or_model_request(self):
        before=dict(self.model.stats)
        code,out,coding=self.run_chat(['/exit'],mode='chat')
        self.assertEqual(code,0,out);coding.assert_not_called()
        self.assertEqual(self.model.stats,before)
        self.assertEqual(self.case.coordinator.store.branches(),())
        self.assertFalse(list(self.home.rglob('chat.json')))

    def test_existing_start_accepts_chat_without_a_filename_wizard(self):
        code,out,coding=self.run_chat(['/chat','Help me plan.','/exit'])
        self.assertEqual(code,0,out);coding.assert_not_called()
        self.assertEqual(chat_cli._read(self.chat_state())['turn_count'],1)
        self.assertFalse(any('files may' in prompt for prompt in self.prompts))

    def test_resume_talk_keeps_the_same_branch_and_adds_one_turn(self):
        self.run_chat(['First thought.','/exit'],mode='chat')
        state=self.chat_state();before=chat_cli._read(state)
        code,out,coding=self.run_chat(['Second thought.','/exit'],mode='chat',chat_state=state)
        self.assertEqual(code,0,out);coding.assert_not_called()
        after=chat_cli._read(state)
        self.assertEqual(after['chat_id'],before['chat_id']);self.assertEqual(after['turn_count'],2)
        self.assertEqual(after['namespace_id'],before['namespace_id'])

    def test_unfinished_answer_cannot_become_a_coding_source(self):
        self.model.plans=defaultdict(lambda:(257,))
        code,out,coding=self.run_chat(['Explain this.','/code Build now.','/exit'],mode='chat')
        self.assertEqual(code,0,out);coding.assert_not_called()
        self.assertIn('/continue',out)
        chat=chat_cli._read(self.chat_state())
        self.assertEqual(self.case.coordinator.store.get_snapshot(chat['head']['tip'])['controller']['status'],'active')

    def test_unknown_slash_command_is_not_sent_as_a_user_message(self):
        code,out,coding=self.run_chat(['/oops','/exit'],mode='chat')
        self.assertEqual(code,0,out);coding.assert_not_called()
        self.assertIn('Unknown command',out)
        self.assertFalse(list(self.home.rglob('chat.json')))

    def test_coding_failure_exits_through_coding_recovery_instead_of_chatting_again(self):
        code,out,coding=self.run_chat(['/code Make a page.'],mode='chat',coding_error=RuntimeError('coding admission failed'))
        self.assertEqual(code,2,out);coding.assert_called_once()
        self.assertIn('coding admission failed',out)

    def test_external_tip_move_rejects_coding_selection_without_model_work(self):
        self.run_chat(['Talk first.','/exit'],mode='chat')
        state=self.chat_state();chat=chat_cli._read(state);head=self.case.coordinator.store.head(chat['branch'])
        self.case.coordinator.store.move(head.name,head.revision,head.root,'external-retry')
        before=dict(self.model.stats)
        with guided_cli._temporary_api_key('cpu-flow-secret'):
            with self.assertRaisesRegex(ValueError,'moved outside'):
                chat_cli.coding_source(state)
        self.assertEqual(self.model.stats,before)
        self.assertEqual(chat_cli._read(state)['head'],chat['head'])

    def test_unsent_queue_prevents_picking_an_older_coding_source(self):
        self.run_chat(['Talk first.','/exit'],mode='chat')
        state=self.chat_state()
        chat_cli._queue_write(state,[dict(operation_id='local-followup',message='Keep this detail.',max_tokens=16)])
        from branchwrite.cow_client import OperationIndeterminate
        with self.assertRaisesRegex(OperationIndeterminate,'unsent'):
            chat_cli.coding_source(state)

    def test_resume_cannot_silently_select_a_different_profile(self):
        self.run_chat(['Talk first.','/exit'],mode='chat')
        state=self.chat_state();before=dict(self.model.stats)
        connection=json.loads(self.connection.read_text());connection['execution_profile_id']='different'
        self.connection.write_text(json.dumps(connection))
        code,out,coding=self.run_chat([],mode='chat',chat_state=state)
        self.assertEqual(code,2,out);coding.assert_not_called()
        self.assertIn('different saved server/profile',out)
        self.assertEqual(self.model.stats,before)

class TalkEntrypointTests(unittest.TestCase):
    def test_talk_uses_the_same_guided_setup_without_saving_the_key(self):
        from branchwrite.__main__ import main
        with patch('branchwrite.guided_cli.run',return_value=0) as run:
            self.assertEqual(main(['talk']),0)
        run.assert_called_once_with(mode='chat',chat_state=None,save_api=False)
