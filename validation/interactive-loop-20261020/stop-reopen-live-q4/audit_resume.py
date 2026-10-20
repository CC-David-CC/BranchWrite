import json
from pathlib import Path
from branchwrite.records import RuntimeLog,Artifact,decode
from branchwrite.kernel import FrameKernel
out=Path(__file__).parent;result=json.loads((out/'result.json').read_text());states=list((out/'session/turns').iterdir());assert len(states)==1
rows=[]
with RuntimeLog(states[0]/'ledger',read_only=True) as log:
 for f in FrameKernel(log).frames():
  if f['contract']!=('COWNativeReceipt','record') or f['state']!='Closed':continue
  d=decode(log.read_artifact(Artifact(*f['result'])))[2];r=json.loads(log.read_artifact(Artifact(*d['response'])));a=r['answer']
  rows.append(dict(operation_id=d['operation_id'],source=r['source_binding'],snapshot=r['receipt']['snapshot'],tokens=len(a['tokens']),forward_tokens=a['counter_deltas']['forward_tokens'],stopped=a['stopped'],grammar_complete=a['grammar_complete'],counter_deltas=a['counter_deltas']))
original=next(r for r in rows if r['operation_id']==result['pending_when_stopped']['operation_id'])
assert original['tokens']==1 and not original['stopped'] and not original['grammar_complete']
continuations=[r for r in rows if r['source']['snapshot']==original['snapshot']]
assert len(continuations)==1,continuations
continued=continuations[0]
assert continued['tokens']>0 and continued['forward_tokens']==continued['tokens'],continued
report=dict(status='PASS',scope='installed client process restart; preserved native partial followed by resumed generation',first_operation_id=original['operation_id'],partial_snapshot=original['snapshot'],next_operation=continued['operation_id'],next_source_snapshot=continued['source']['snapshot'],resume_tokens=continued['tokens'],resume_forward_tokens=continued['forward_tokens'],prefix_forward_tokens=continued['forward_tokens']-continued['tokens'],rows=rows)
(out/'receipt-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='rows'}))
