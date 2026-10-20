"""Bounded real Q4 smoke of the generic .bw CLI, not a qualification gate.

Only host setup, one CLI invocation and independent final inspection are here.
The interpreter/model choose every action; this runner never supplies a patch.
"""
import argparse,hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
from types import SimpleNamespace

WORKFLOW=r'''FLOW coding
REPEAT attempts max=16 until=verified exhausted=stop
EXPAND decide from=current task=task profile=control -> proposed
PLAN freeze from=proposed against=world -> plan
ACT perform plan=plan -> outcome
TRANSFORM advance input=proposed contract=cow-source -> current
TRANSFORM feedback input=outcome contract=tool-feedback -> task
VERIFY check input=outcome contract=unit-tests-and-finish -> verified
END
END
'''

def prefix_token_count(store,snapshot):
    # This profile stores even text-only context in the canonical mixed schema.
    from context_time_travel.input_spans import input_count
    _,spans=store.input_lineage(snapshot)
    return input_count(spans)

def finish_progress(tracker,error):
    tracker.finish('PASS' if error is None else 'FAIL',None if error is None else str(error))
    tracker.close()
    return json.loads((tracker.run_dir/'progress.json').read_bytes())

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ['runtime','profile','vision-config','dependencies','output','cache-store']:ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--grammar-layout',choices=['tool-first','json-schema'],default='tool-first')
    ap.add_argument('--sampler',choices=['default','greedy','minp-dry','minp'],default='default')
    ap.add_argument('--workload-config',type=Path,help='Host-owned task/source/grants/workflow and independent checker; never model actions')
    ap.add_argument('--examples',type=Path,help='Reviewed reusable worked examples appended to the system prefix')
    args=ap.parse_args();root=Path(__file__).resolve().parents[1];runtime=args.runtime.resolve(strict=True)
    sys.path[:0]=[str(root),str(runtime),str(runtime/'tools'),str(runtime/'experimental/branching_context/src'),str(runtime/'experimental/branching_context/scripts'),str(args.dependencies)]
    from run_cli_grammar_probe import GrammarProbe,_atomic_json
    from validation.run_basic_loop_html import image_probe_type
    from branchwrite.execution import Executor,Grant
    from branchwrite.tool_registry import ToolRegistry
    from branchwrite.cow_client import CowClient,OperationJournal
    from branchwrite.cow_actions import DEFAULT_THINKING_TOKENS
    workload=None
    if args.workload_config is not None:
        if args.examples is not None:raise ValueError('workload runs use the public CLI bootstrap')
        workload=json.loads(args.workload_config.read_bytes())
        if type(workload) is not dict or set(workload)!={'schema','task_file','source','workflow','grant','verification','checker'} or workload['schema']!=1:
            raise ValueError('closed host workload description required')
        for key in ('task_file','source','workflow'):
            if not Path(workload[key]).is_absolute() or not Path(workload[key]).exists():raise ValueError('absolute existing workload path required')
        checker=workload['checker']
        if type(checker) is not dict or set(checker)!={'argv','files'} or type(checker['argv']) is not list or not checker['argv'] or any(type(v) is not str for v in checker['argv']):
            raise ValueError('trusted independent checker argv and source pins required')
        for name,digest in checker['files'].items():
            if not Path(name).is_absolute() or hashlib.sha256(Path(name).read_bytes()).hexdigest()!=digest:raise ValueError('independent checker source changed')
    args.output.mkdir(mode=0o700,exist_ok=False)
    if args.cache_store.exists():raise ValueError('cache store must be new and uniquely owned')
    args.cache_store.mkdir(mode=0o700,exist_ok=False)
    owner=image_probe_type(GrammarProbe,args.vision_config)
    probe=owner(SimpleNamespace(runtime_root=runtime,profile=args.profile,store=args.cache_store,run_dir=args.output,dependency_root=args.dependencies,ram_gib=96,disk_gib=8))
    probe.record.update(scope=__doc__,status='RUNNING',task_completed=False,source_unchanged=False,cli_exit=None,
        numerical_qualification='NOT_RUN',cache_storage='tmpfs/disposable; no reboot durability claim',new_thinking_budget=DEFAULT_THINKING_TOKENS,
        bw_sources={str(q.relative_to(root)):hashlib.sha256(q.read_bytes()).hexdigest() for folder in ['branchwrite','validation'] for q in (root/folder).glob('*.py')})
    error=None;cli=None
    try:
        probe._imports();profile=json.loads(args.profile.read_bytes());probe.runtime_closure(profile,runtime)
        probe.record['profile_sha256']=hashlib.sha256(args.profile.read_bytes()).hexdigest()
        source=args.output/'input-source'
        if workload is None:
            source.mkdir(mode=0o700);(source/'tests').mkdir(mode=0o700)
            original=b'def add(a, b):\n    return a - b\n';(source/'calc.py').write_bytes(original)
            (source/'tests/__init__.py').write_bytes(b'')
            (source/'tests/test_calc.py').write_text('import unittest\nfrom calc import add\nclass Addition(unittest.TestCase):\n def test_ordinary(self): self.assertEqual(add(7, 3), 10)\n def test_negative(self): self.assertEqual(add(-2, 5), 3)\n def test_zero(self): self.assertEqual(add(0, 0), 0)\n',newline='\n')
            grant=Grant(('calc.py',),True,read_paths=('calc.py',))
        else:
            shutil.copytree(workload['source'],source,symlinks=True)
            g=workload['grant'];grant=Grant(tuple(g['edit_paths']),g['allow_tests'],read_paths=tuple(g['read_paths']),create_paths=tuple(g['create_paths']))
            probe.record['workload_config_sha256']=hashlib.sha256(args.workload_config.read_bytes()).hexdigest()
            probe.record['workload_task_sha256']=hashlib.sha256(Path(workload['task_file']).read_bytes()).hexdigest()
        original_inventory={str(q.relative_to(source)):hashlib.sha256(q.read_bytes()).hexdigest() for q in source.rglob('*') if q.is_file() and not q.is_symlink()}
        state=args.output/'workflow-state';state.mkdir(mode=0o700)
        executor=Executor.create(source,state/'world')
        registry=ToolRegistry(executor,grant);schema=registry.model_schema()
        registry_path=args.output/'grammar-registry.json'
        from branchwrite.coding_defaults import grammar_registry
        payload=grammar_registry(registry)
        if args.grammar_layout=='json-schema':
            payload['states']['BW_TOOLS']['source']['final']=dict(format='json_schema',source=schema)
        _atomic_json(registry_path,payload)
        probe.record['grammar_layout']=args.grammar_layout
        probe.tracker=probe.ProgressTracker(args.output,'autonomous-workflow-Q4').start();probe.start_service(registry_path)
        client=CowClient.http(probe.ready_url(probe.service.ready),journal=OperationJournal(args.output/'setup-operations'),api_key=probe.secret,endpoint_pin='owned-autonomous-q4-smoke-'+probe.run_id)
        from branchwrite.coding_defaults import generation_profile,system_prefix,workflow_source
        cfg=dict(schema=1,source=str(source),run_id='autonomous-'+probe.run_id,
            grant=dict(edit_paths=['calc.py'],read_paths=['calc.py'],create_paths=[],allow_tests=True),
            bindings=dict(task=dict(type='Text',value='Fix calc.py so add(a, b) adds its inputs. Read it, make the smallest correction, run the existing unit tests and finish.')),
            cow=dict(endpoint_url=probe.ready_url(probe.service.ready),endpoint_pin=client.endpoint_pin,model_contract_id=profile['model_contract_id'],execution_profile_id=profile['execution_profile_id'],eos_tokens=profile['execution']['eos_tokens'],branch='coding',mode='ask'))
        if workload is not None:
            cfg['grant']=workload['grant'];cfg['verification']=workload['verification']
            cfg['bindings']['task']['value']=Path(workload['task_file']).read_text(encoding='utf8')
        if args.examples is not None:
            # Explicit legacy control: retain earlier example/source arrangement.
            ns=client.create_namespace('Autonomous coding smoke','workflow-ns')['namespace_id']
            system=('You are BranchWrite, an autonomous coding worker in an owned workspace. Use exactly one registered tool action per response. '
                'Read a file before replacing it; use the exact SHA256 from the observation. Tool results are real and appear in the next user message. '
                'After editing, run_tests with suite unit. If tests fail, read, fix and test again. Only request finish after tests pass. '
                'You may edit calc.py only. You cannot edit tests or grant yourself tools. Do not use shell commands. '
                'Return a JSON tool proposal using this schema: '+json.dumps(schema,sort_keys=True))
            examples=args.examples.read_text(encoding='utf8');system+='\n\n'+examples
            probe.record['examples']=dict(path=str(args.examples),sha256=hashlib.sha256(args.examples.read_bytes()).hexdigest())
            prepared=client.load_context('coding',ns,[dict(role='system',content=system)],'workflow-root')
            probe.record['prefix_consumed_tokens']=prefix_token_count(probe.store,prepared.receipt.snapshot)
        else:
            cfg['cow']['bootstrap']='coding'
            probe.record['prefix_owner']='public CLI coding bootstrap; builtin three examples'
        policies={'greedy':dict(temperature=0),'minp':dict(temperature=0.70,min_p=0.05,top_k=0,top_p=1.0),
            'minp-dry':generation_profile()['settings']}
        if args.sampler!='default':
            cfg['profiles']={'control':generation_profile()};cfg['profiles']['control']['settings']=policies[args.sampler]
        probe.record['sampler']=dict(name=args.sampler,settings=(generation_profile() if args.sampler=='default' else cfg['profiles']['control'])['settings'])
        config_path=args.output/'host.json';_atomic_json(config_path,cfg)
        program=args.output/'coding.bw';program.write_text(Path(workload['workflow']).read_text() if workload is not None else (workflow_source() if args.examples is None else WORKFLOW),newline='\n')
        command=[sys.executable,'-B','-m','branchwrite','run',str(program),'--config',str(config_path),'--state',str(state),'--max-steps','1024']
        probe.record['cli_argv']=command;probe.phase('autonomous-cli-run')
        with (args.output/'cli.stdout').open('xb') as out,(args.output/'cli.stderr').open('xb') as err:
            cli=subprocess.Popen(command,cwd=root,env={**os.environ,'BW_COW_API_KEY':probe.secret},stdin=subprocess.DEVNULL,stdout=out,stderr=err,close_fds=True,start_new_session=True)
            probe.record['cli_pid']=cli.pid;start=time.monotonic();last=start
            while cli.poll() is None:
                now=time.monotonic()
                if now-start>900:raise TimeoutError('autonomous CLI exceeded900s; retain unresolved work')
                if now-last>=30:
                    probe.record['elapsed_cli_seconds']=now-start
                    probe.record['retained_client_records']=len(list((state/'cow-operations').glob('*.json')))
                    probe.publish();print(json.dumps(dict(phase='autonomous-cli-run',elapsed_seconds=now-start,pid=cli.pid)),flush=True);last=now
                time.sleep(0.5)
        probe.record['cli_exit']=cli.returncode;probe.record['cli_seconds']=time.monotonic()-start
        probe.record['cli_report']=json.loads((args.output/'cli.stdout').read_bytes())
        if cli.returncode!=0:raise RuntimeError('generic CLI did not reach verified completion')
        workspace=state/'world/workspace'
        unchanged=original_inventory=={str(q.relative_to(source)):hashlib.sha256(q.read_bytes()).hexdigest() for q in source.rglob('*') if q.is_file() and not q.is_symlink()}
        probe.record.update(source_unchanged=unchanged,cli_absent=not (Path('/proc')/str(cli.pid)).exists())
        if workload is None:
            actual=(workspace/'calc.py').read_bytes();probe.record['actual_source_sha256']=hashlib.sha256(actual).hexdigest()
            import ast
            tree=ast.parse(actual)
            probe.record['addition_ast']=any(isinstance(node,ast.BinOp) and isinstance(node.op,ast.Add) for node in ast.walk(tree))
            final_executor=Executor(source,state/'world',workspace)
            final_tests=final_executor.run_tests('independent-final-tests',grant)
            probe.record['independent_final_test_exit']=final_tests.exit_code
            probe.record['independent_final_test_stderr']=final_tests.stderr.read_bytes().decode('utf8')
            independently_verified=probe.record['addition_ast'] and final_tests.exit_code==0
        else:
            # Host-selected protected checker, not candidate code or model argv.
            # File-only checks may read on host; executable/browser checks must
            # themselves retain the existing authorized sandbox boundary.
            checker=workload['checker']
            for name,digest in checker['files'].items():
                if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=digest:raise ValueError('independent checker changed during run')
            argv=[v.replace('{workspace}',str(workspace)).replace('{output}',str(args.output/'protected-check')) for v in checker['argv']]
            final_check=subprocess.run(argv,stdin=subprocess.DEVNULL,capture_output=True,timeout=60)
            (args.output/'protected-check.stdout').write_bytes(final_check.stdout);(args.output/'protected-check.stderr').write_bytes(final_check.stderr)
            probe.record['independent_checker']=dict(argv=argv,exit_code=final_check.returncode,files=checker['files'])
            independently_verified=final_check.returncode==0
        from branchwrite.records import RuntimeLog,Artifact,decode
        from branchwrite.kernel import FrameKernel
        with RuntimeLog(state/'ledger') as log:
            kernel=FrameKernel(log);tools=[];models=[]
            root_inputs=decode(log.read_artifact(Artifact(*kernel.frame('program')['inputs'])))
            prefix_tip=root_inputs['bindings']['current'][1]['head']['tip']
            probe.record['prefix_consumed_tokens']=prefix_token_count(probe.store,prefix_tip)
            for frame in kernel.frames():
                if frame['state']!='Closed':continue
                if frame['contract'][0] in ('ToolOutcome','ModelOutput'):
                    value=decode(log.read_artifact(Artifact(*frame['result'])))[2]
                    (tools if frame['contract'][0]=='ToolOutcome' else models).append(value)
            probe.record['tool_outcomes']=tools;probe.record['model_outputs']=models;probe.record['workflow_events']=log.event_count
        probe.record['task_completed']=all((probe.record['cli_report']['verified'],probe.record['source_unchanged'],independently_verified))
        if not probe.record['task_completed']:raise RuntimeError('independent final inspection failed')
        probe.record['status']='BOUNDED_AUTONOMOUS_Q4_PASS'
    except BaseException as exc:
        error=exc;probe.record['status']='FAIL';probe.record['failures'].append(dict(type=type(exc).__name__,message=str(exc)))
        if cli is not None and cli.poll() is None:
            import signal
            os.killpg(cli.pid,signal.SIGTERM)
            try:cli.wait(timeout=10)
            except subprocess.TimeoutExpired:os.killpg(cli.pid,signal.SIGKILL);cli.wait(timeout=10)
    finally:
        try:probe.stop_service()
        except BaseException as exc:
            error=error or exc;probe.record['status']='FAIL';probe.record['failures'].append(dict(type=type(exc).__name__,message=str(exc)))
        if probe.tracker:probe.record['progress']=finish_progress(probe.tracker,error)
        probe.publish()
    return int(error is not None)
if __name__=='__main__':raise SystemExit(main())
