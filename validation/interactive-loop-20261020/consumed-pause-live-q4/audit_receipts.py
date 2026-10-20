import json
from pathlib import Path
from branchwrite.records import RuntimeLog,Artifact,decode
from branchwrite.kernel import FrameKernel
out=Path(__file__).parent;rows=[]
for state in sorted((out/'session/turns').iterdir()):
 with RuntimeLog(state/'ledger',read_only=True) as log:
  frames=FrameKernel(log).frames();native=[]
  for f in frames:
   if f['contract']!=('COWNativeReceipt','record') or f['state']!='Closed':continue
   payload=decode(log.read_artifact(Artifact(*f['result'])))[2]
   ref=payload.get('response')
   if ref is None:
    native.append(dict(frame=f['name'] if 'name' in f else f.get('id'),keys=sorted(payload)));continue
   data=json.loads(log.read_artifact(Artifact(*ref)));answer=data['answer']
   native.append(dict(operation_id=payload.get('operation_id'),tokens=len(answer.get('tokens',[])),answer_keys=sorted(answer),source_binding=data.get('source_binding'),receipt=data.get('receipt'),grammar_complete=answer.get('grammar_complete'),stopped=answer.get('stopped'),counter_deltas=answer.get('counter_deltas'),generation_seconds=answer.get('generation_seconds'),request_seconds=answer.get('request_seconds')))
  launch=json.loads((state/'coding-launch.json').read_text())['launch']
  rows.append(dict(turn=state.name,model_outputs=sum(f['contract']==('ModelOutput','record') and f['state']=='Closed' for f in frames),native=native,launch=launch))
assert len(rows)==2
assert rows[0]['model_outputs']==0 and len(rows[0]['native'])==1
assert rows[0]['native'][0]['tokens']==1
assert rows[0]['native'][0]['stopped'] is False and rows[0]['native'][0]['grammar_complete'] is False
original=json.loads((out/'result.json').read_text())
assert rows[0]['native'][0]['operation_id']==original['pending_when_steered']['operation_id']
assert original['goal'] in rows[1]['launch']['config']['bindings']['task']['value'] and original['steering'] in rows[1]['launch']['config']['bindings']['task']['value']
(out/'receipt-audit.json').write_text(json.dumps(dict(rows=rows),indent=2)+'\n')
print(json.dumps([dict(turn=r['turn'],model_outputs=r['model_outputs'],native_responses=len(r['native']),tokens=[n.get('tokens') for n in r['native']]) for r in rows]))
