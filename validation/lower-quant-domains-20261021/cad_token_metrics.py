
from pathlib import Path
import argparse,base64,json

def metrics(folder):
 rows=[]
 for p in Path(folder).glob('*.json'):
  d=json.loads(p.read_text());a=d.get('answer')
  if not d.get('operation_id','').startswith('bwnative') or not isinstance(a,dict):continue
  req=json.loads(base64.b64decode(d['body_b64']));t=a.get('thinking') or {};progress=t.get('progress')
  rows.append(dict(revision=req['revision'],tokens=len(a['tokens']),progress=progress,complete=t.get('complete'),generation_seconds=a.get('generation_seconds'),request_seconds=a.get('request_seconds')))
 rows.sort(key=lambda x:x['revision']);last=dict(reasoning_tokens=0,final_tokens=0,closing_tokens=0);reasoning=final=closing=total=0;ended=True;episodes=0
 for row in rows:
  if ended:last=dict(reasoning_tokens=0,final_tokens=0,closing_tokens=0)
  p=row['progress'];assert p is not None,'no native token phase accounting'
  delta={k:p[k]-last[k] for k in last};assert min(delta.values())>=0,('unexpected parser reset',row)
  reasoning+=delta['reasoning_tokens'];final+=delta['final_tokens'];closing+=delta['closing_tokens'];total+=row['tokens'];last={k:p[k] for k in last};ended=row['complete']
  if ended:episodes+=1
 boundary=total-reasoning-final;assert boundary>=closing
 return dict(completed_requests=len(rows),completed_actions=episodes,generated_tokens=total,thinking_tokens=reasoning,action_json_tokens=final,boundary_and_stop_tokens=boundary,closing_tokens=closing,generation_seconds=sum(x['generation_seconds'] for x in rows),request_seconds=sum(x['request_seconds'] for x in rows),last_request_action_complete=ended,requests=rows,scope='completed native request receipts only; pending request tokens excluded; input/prefill tokens excluded')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('journal',type=Path);args=p.parse_args();print(json.dumps(metrics(args.journal),indent=2))
