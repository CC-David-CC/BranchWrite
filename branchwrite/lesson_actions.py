"""Read settled coding actions from BW's original capture, without dispatch.

This is an export view, never a second workflow transcript or execution cursor.
Correctness, lesson selection and training approval belong to the caller.
"""
import copy
import hashlib

from .lesson_capture import CaptureRefused, read_capture, _read, _json
from .records import RuntimeLog, Artifact, decode, encode
from .kernel import FrameKernel
from .cow_client import CowClient, OperationJournal, OperationIntent
from .lesson_capture import _NoNetwork
from .model_dispatch import ModelAdapter, _flow, _prior
from .tool_registry import _OBSERVED_TOOLS


def captured_action_turns(directory, *, expected_capture_id):
    """Validate a single text-only context chain and its admitted tool outcomes.

    Original model tokens remain evidence only. Consumers must render the logical
    messages with the destination model's actual tokenizer and COW append rules.
    Forked, retried, thinking, image and unfinished turns require their own
    qualification and are refused here, rather than flattened into fake history.
    """
    capture = read_capture(directory, expected_capture_id=expected_capture_id)
    manifest = capture.manifest
    journal = OperationJournal(capture.directory/'cow-operations')
    roots = []
    for path in sorted(journal.directory.iterdir()):
        record = _json(_read(path))
        route = record['path']
        if route in ('/cow/fork', '/cow/text/prepare'):
            raise CaptureRefused('action export requires one original context-only bootstrap')
        if route == '/cow/text/context':
            roots.append((record, _json(journal.decode_body(record))))
    if len(roots) != 1:
        raise CaptureRefused('action export requires one original context-only bootstrap')
    record, bootstrap = roots[0]
    messages = bootstrap.get('messages')
    if (type(messages) is not list or len(messages) != 1
            or set(messages[0]) != {'role', 'content'}
            or messages[0]['role'] != 'system' or type(messages[0]['content']) is not str):
        raise CaptureRefused('one recorded text system bootstrap required')
    head = record['receipt']['branch']
    cow = manifest['launch']['config']['cow']
    client = CowClient(_NoNetwork(), journal=journal, endpoint_url=cow['endpoint_url'], endpoint_pin=cow['endpoint_pin'])
    mapping = {}
    for path in sorted(journal.directory.iterdir()):
        row = _json(_read(path))
        if row['path'] == '/cow/grammars':
            if mapping:
                raise CaptureRefused('ambiguous original grammar registration')
            intent = OperationIntent(row['operation_id'], 'POST', row['path'], journal.decode_body(row),
                None, None, None, cow['endpoint_pin'])
            mapping = client._validate_nonstream(intent, row['receipt'])['states']
    adapter = ModelAdapter(client, run_id=manifest['launch']['config']['run_id'],
        model_contract_id=manifest['model_contract_id'], execution_profile_id=manifest['execution_profile_id'],
        eos_tokens=tuple(cow['eos_tokens']), grammar_mapping=mapping)
    turns = []
    with RuntimeLog(capture.directory/'ledger', read_only=True) as log:
        kernel = FrameKernel(log)
        frames = kernel.frames()
        models = [f for f in frames if f['contract'] == ('ModelOutput', 'record')]
        tools = [f for f in frames if f['contract'] == ('ToolOutcome', 'record')]
        if not 1 <= len(models) <= 128 or len(models) != len(tools):
            raise CaptureRefused('each bounded logical action must have one actual tool outcome')
        pending = {}
        for frame in models:
            frame, plan = _flow(kernel, adapter, frame['id'])
            config = plan['config']
            if ('planning' in plan or config['output_format'] != 'constrained'
                    or type(config['content']) is not str or config['mode'] not in ('ask', 'append_user')):
                raise CaptureRefused('only completed constrained text action chains are supported')
            key = encode(plan['source'])
            if key in pending:
                raise CaptureRefused('multiple continuations of the same source cannot be flattened')
            pending[key] = (frame, plan)
        used_tools = set()
        while pending:
            entry = pending.pop(encode(head), None)
            if entry is None:
                raise CaptureRefused('action chain has a gap, fork, retry or foreign source')
            frame, plan = entry
            if plan['config']['mode'] != ('ask' if not turns else 'append_user'):
                raise CaptureRefused('action chain changes its context boundary')
            values, _, used = _prior(kernel, adapter, frame, plan, frame['epoch'])
            if not values:
                raise CaptureRefused('logical action has no original native responses')
            last = values[-1][1]
            if (last.answer['tokens'][-1] not in adapter.eos_tokens or last.answer.get('stopped') is False
                    or last.answer.get('grammar_complete') is not True):
                raise CaptureRefused('action did not finish at its original native grammar/EOS boundary')
            text = ''.join(result.answer['text'] for _, result in values)
            expected = dict(schema=1, model_frame=frame['id'], plan_sha256=frame['inputs'][0],
                output_format=plan['config']['output_format'], text=text, native_receipt=dict(last.receipt.raw),
                source_snapshot=plan['source']['tip'], consumed_output_tokens=used,
                request_count=len(values), responses=tuple(value['response'] for value, _ in values))
            returned = decode(log.read_artifact(Artifact(*frame['result'])))
            if returned != ('bw.result.v1', ('ModelOutput', 'record'), expected,
                            tuple(value['response'] for value, _ in values)):
                raise CaptureRefused('logical output differs from its original consumed native responses')
            action = _json(text)
            if type(action) is not dict or set(action) != {'tool', 'arguments'}:
                raise CaptureRefused('one original JSON tool action required')
            siblings = [f for f in tools if f['parent'] == frame['parent']]
            if len(siblings) != 1:
                raise CaptureRefused('logical action has no unique sibling tool outcome')
            tool = siblings[0]
            tool_plan = decode(log.read_artifact(Artifact(*tool['inputs'])))
            outcome = decode(log.read_artifact(Artifact(*tool['result'])))[2]
            arguments = dict(tool_plan[4])
            if tool_plan[3] in _OBSERVED_TOOLS:
                observed = tool_plan[7]
                source = arguments.pop('source_sha256', None)
                if (type(observed) is not tuple or len(observed) != 3
                        or observed != (tool_plan[2], arguments.get('path'), source)):
                    raise CaptureRefused('host-bound edit lost its original source observation')
            if (tool['id'] in used_tools or (tool_plan[3], arguments) != (action['tool'], action['arguments'])
                    or tool['id'] not in {t['frame'] for t in manifest['evidence']['tools']}):
                raise CaptureRefused('action differs from its actual admitted tool arguments/outcome')
            used_tools.add(tool['id'])
            turns.append(dict(index=len(turns), input_mode=plan['config']['mode'],
                user_content=plan['config']['content'], assistant_text=text,
                action=action, model_frame=frame['id'], model_plan_sha256=frame['inputs'][0],
                model_result_sha256=frame['result'][0], native_requests=len(values),
                original_consumed_tokens=used, tool_frame=tool['id'], tool_plan_sha256=tool['inputs'][0],
                tool_result_sha256=tool['result'][0], outcome=outcome))
            head = dict(last.receipt.raw['branch'])
    result = dict(schema=1, kind='bw.captured-action-turns.v1', capture_id=capture.capture_id,
        model_contract_id=manifest['model_contract_id'], execution_profile_id=manifest['execution_profile_id'],
        bootstrap_messages=messages, turns=turns, independently_verified=False, training_approved=False,
        export_only=True, source_sha256=hashlib.sha256(_read(__file__)).hexdigest())
    return copy.deepcopy(result)
