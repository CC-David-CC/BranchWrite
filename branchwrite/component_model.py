"""Independent model interpretation checks, before an autonomous tool workflow.

The input observations must already pass real terminal component assertions.
Grammar constrains report shape, never the expected answers. A passing result
does not prove tool selection, autonomous completion or OOD generalization.
"""
import argparse,hashlib,json,threading,time,uuid
from pathlib import Path
from .cow_client import CowClient,OperationJournal
from .cow_actions import completed_thinking_text

FIELDS={'disposition':str,'exit_code':(int,type(None)),'stdout':str,'stderr':str,
        'stdout_bytes':int,'stderr_bytes':int,'stdout_lossy':bool,'stderr_lossy':bool,
        'stdout_final_lf':bool,'stderr_final_lf':bool}
def schema():
    properties={}
    for key,kind in FIELDS.items():
        properties[key]={'type':['integer','null']} if key=='exit_code' else {'type':'boolean' if kind is bool else 'integer' if kind is int else 'string'}
    return dict(type='object',properties=properties,required=list(properties),additionalProperties=False)
def grammar_registry():
    return dict(schema=1,states={'COMPONENT_REPORT':dict(format='thinking',source=dict(schema=1,max_tokens=4096,final=dict(format='json_schema',source=schema())))})
def _pairs(items):
    result={}
    for key,value in items:
        if key in result:raise ValueError('duplicate report field')
        result[key]=value
    return result
def parse_report(text):
    value=json.loads(text,object_pairs_hook=_pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite number')))
    if type(value) is not dict or set(value)!=set(FIELDS):raise ValueError('report fields differ')
    for key,kind in FIELDS.items():
        kinds=kind if isinstance(kind,tuple) else (kind,)
        if type(value[key]) not in kinds:raise ValueError('wrong report type: '+key)
    return value
def reference_report(observation):
    if observation.get('status')!='PASS' or not observation.get('checks') or not all(v is True for v in observation['checks'].values()):
        raise ValueError('a completed passing real component observation is required')
    actual=observation['actual'];view=observation['feedback']
    value=dict(disposition=actual['disposition'],exit_code=actual['exit_code'])
    for stream in ('stdout','stderr'):
        row=actual[stream];raw=bytes.fromhex(row['hex'])
        if row['bytes']!=len(raw) or row['sha256']!=hashlib.sha256(raw).hexdigest():raise ValueError('raw observation digest mismatch')
        text=raw.decode('utf8','replace')
        if view[stream]!=text:raise ValueError('display observation mismatch')
        value[stream]=text;value[stream+'_bytes']=len(raw)
        try:raw.decode('utf8');lossy=False
        except UnicodeDecodeError:lossy=True
        if view[stream+'_display']['lossy'] is not lossy:raise ValueError('lossiness observation mismatch')
        value[stream+'_lossy']=lossy;value[stream+'_final_lf']=raw.endswith(b'\n')
    return value
def compare_report(text,expected):
    value=parse_report(text)
    return value,{key:dict(expected=expected[key],actual=value[key]) for key in expected if type(expected[key]) is not type(value[key]) or expected[key]!=value[key]}
def question(observation):
    # Do not include the preauthored expected result, case verdict or checker.
    view=observation['feedback']
    visible={key:value for key,value in view.items() if key not in {'operation_id','plan_sha256','observation'}}
    return ('Interpret this one real terminal observation. Return only the requested JSON report. '
        'Copy stdout/stderr exactly as their display strings, retaining literal dollars, quotes, Unicode and line endings. '
        'Byte counts describe original artifacts, not re-encoded display text. *_final_lf means the raw stream ends in byte0A; '
        'CRLF also ends in LF, literal backslash+n does not. Status/disposition must come from this result, not optimistic text. '
        'Do not execute commands, repair intentional failures or report additional probes.\n'
        +json.dumps(visible,ensure_ascii=True,sort_keys=True))
def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('cases','prefix','credentials','output-dir'):ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--endpoint',required=True);ap.add_argument('--label',required=True)
    ap.add_argument('--dry-multiplier',type=float,default=0)
    args=ap.parse_args(argv)
    cases=json.loads(args.cases.read_bytes())
    expected=[reference_report(case['observation']) for case in cases]
    prefix=args.prefix.read_text(encoding='utf8')
    creds=json.loads(args.credentials.read_bytes())
    out=args.output_dir;out.mkdir(mode=0o700)
    report=dict(schema=1,status='RUNNING',scope='Independent model report extraction; no autonomous tool loop or numerical oracle',
        label=args.label,prefix_sha256=hashlib.sha256(prefix.encode()).hexdigest(),prefix_bytes=len(prefix.encode()),cases=[],start=time.time())
    stop=threading.Event()
    def heartbeat():
        while not stop.wait(30):
            print(json.dumps(dict(phase='model-component-check',label=args.label,completed=len(report['cases']),elapsed=time.time()-report['start'])),flush=True)
    def write():
        tmp=out/'report.partial';tmp.write_text(json.dumps(report,indent=2,ensure_ascii=True)+'\n');tmp.replace(out/'report.json')
    thread=threading.Thread(target=heartbeat,daemon=True);thread.start()
    client=CowClient.http(args.endpoint,journal=OperationJournal(out/'operations'),api_key=creds['api_key'])
    settings=dict(temperature=.7,min_p=.05,top_k=60,top_p=.95,dry_multiplier=args.dry_multiplier,
                  dry_base=1.75,dry_allowed_length=2,dry_penalty_last_n=256)
    report['settings']=settings;report['model_contract_id']=creds['model_contract_id'];report['execution_profile_id']=creds['execution_profile_id']
    try:
        ns=client.create_namespace('Independent terminal components')['namespace_id']
        stamp=uuid.uuid4().hex[:16];root='tc-root-'+stamp
        t=time.monotonic();prepared=client.load_context(root,ns,[dict(role='system',content=prefix)])
        report['context_creation_seconds']=time.monotonic()-t;report['prefix_receipt']=prepared.receipt.raw
        write()
        for index,(case,truth) in enumerate(zip(cases,expected)):
            branch='tc-'+stamp+'-'+str(index)
            head=client.fork(root,prepared.receipt.snapshot,branch,'tcf-'+uuid.uuid4().hex)
            t=time.monotonic();result=client.ask(branch,head.revision,'tcq-'+uuid.uuid4().hex,question(case['observation']),2048,
                settings=settings,grammar_state='COMPONENT_REPORT')
            segments=[];output_tokens=0
            for n in range(32):
                segments.append(dict(operation_id=result.operation_id,receipt=result.receipt.raw,answer=dict(result.answer)))
                output_tokens+=len(result.answer.get('tokens',[]))
                if result.answer.get('thinking',{}).get('complete') is True:break
                head=result.receipt.branch
                result=client.continue_(branch,head.revision,'tcr-'+uuid.uuid4().hex,2048)
            text=completed_thinking_text(result,creds['eos_tokens'])
            value,mismatches=compare_report(text,truth)
            record=dict(id=case['id'],status='PASS' if not mismatches else 'FAIL',actual=value,expected=truth,
                mismatches=mismatches,thinking=dict(result.answer['thinking']),output_tokens=output_tokens,
                wall_seconds=time.monotonic()-t,request_count=len(segments),receipt_snapshot=result.receipt.snapshot)
            (out/('case-'+str(index)+'.json')).write_text(json.dumps(dict(record=record,question=question(case['observation']),segments=segments),indent=2)+'\n')
            report['cases'].append(record);write()
            print(json.dumps({key:record[key] for key in ('id','status','wall_seconds','output_tokens')}),flush=True)
        report['status']='PASS' if all(c['status']=='PASS' for c in report['cases']) else 'FAIL'
    except Exception as exc:
        report.update(status='ERROR',error=dict(type=type(exc).__name__,message=str(exc)));raise
    finally:
        report['elapsed_seconds']=time.time()-report['start'];stop.set();thread.join(2);write()
    return int(report['status']!='PASS')
if __name__=='__main__':raise SystemExit(main())
