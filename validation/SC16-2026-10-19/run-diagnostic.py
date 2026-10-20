"""Bounded installed CowClient diagnostic; no coding/tool acceptance claim."""
from pathlib import Path
import json,os,socket,subprocess,time,threading,sys,hashlib
from branchwrite.cow_client import CowClient,OperationJournal
b=Path(__file__).parent
fixture=json.loads((b/'fixture.json').read_text());credentials=json.loads((b/'ssh/credentials.json').read_text())
result=dict(status='RUNNING',diagnostic_only=True,client_host=os.uname().nodename,
 client_module=__import__('branchwrite').__file__,fixture_sha256=hashlib.sha256((b/'fixture.json').read_bytes()).hexdigest(),measurements=[])
phase='starting';finished=threading.Event();start=time.monotonic()
def save():
 p=b/'result.partial';p.write_text(json.dumps(result,indent=2));p.replace(b/'result.json')
def heartbeat():
 while not finished.wait(30):
  with (b/'heartbeat.jsonl').open('a') as out:
   out.write(json.dumps(dict(phase=phase,elapsed_seconds=time.monotonic()-start,pid=os.getpid()))+'\n')
thread=threading.Thread(target=heartbeat,daemon=True);thread.start()
with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
key=b/'ssh'
argv=['ssh','-N','-o','BatchMode=yes','-o','ExitOnForwardFailure=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','-o','HostKeyAlias=bw-llm60','-o','UserKnownHostsFile='+str(key/'known_hosts'),'-i',str(key/'id_ed25519'),'-L','127.0.0.1:'+str(port)+':127.0.0.1:'+str(credentials['port']),'dflanag3@llm-60']
tunnel=None;error=None
try:
 save()
 with (b/'ssh.stderr').open('x') as err:
  tunnel=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=err)
 deadline=time.monotonic()+20
 while True:
  if tunnel.poll() is not None:raise RuntimeError('owned SSH listener exited')
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=1):break
  except OSError:
   if time.monotonic()>deadline:raise TimeoutError('owned SSH listener not ready')
   time.sleep(.1)
 client=CowClient.http('http://127.0.0.1:'+str(port),journal=OperationJournal(b/'operations'),
  api_key=credentials['api_key'],endpoint_pin='ssh-pinned-owned-llm60-api')
 for label,limit in [('warmup',fixture['warmup_tokens']),('baseline',fixture['max_tokens']),('profile',fixture['max_tokens'])]:
  phase=label;result['phase']=phase;save()
  branch='sc16-'+label+'-q8-dev16-20261019-v1'
  head=client.fork(fixture['source_branch'],fixture['source_snapshot'],branch,'sc16-'+label+'-fork-20261019-v1')
  t=time.monotonic()
  generated=client.ask(branch,head.revision,'sc16-'+label+'-ask-20261019-v1',fixture['content'],limit,
   settings=fixture['settings'],grammar_state=fixture['grammar_state'])
  elapsed=time.monotonic()-t
  assert generated.receipt.raw['model_contract_id']==credentials['model_contract_id']
  assert generated.receipt.raw['execution_profile_id']==credentials['execution_profile_id']
  answer=dict(generated.answer)
  result['measurements'].append(dict(label=label,limit=limit,elapsed_seconds=elapsed,
   actual_tokens=len(answer['tokens']),answer=answer,receipt=dict(generated.receipt.raw)))
  save()
 baseline=result['measurements'][1];profile=result['measurements'][2]
 assert baseline['actual_tokens']>0
 assert baseline['answer']['tokens']==profile['answer']['tokens'],'matching diagnostic token IDs differ'
 assert baseline['answer']['thinking']==profile['answer']['thinking'],'matching diagnostic thinking fields differ'
 result.update(status='BOUNDED_DIAGNOSTIC_PAIR_PASS',tokens_identical=True,thinking_fields_identical=True,
  numerical_oracle='NOT_RUN',native_modules_loaded=sorted({'context_time_travel','serve','torch','llama_cpp'}.intersection(sys.modules)),
  scope='Same-input token/controller-facing diagnostic only; not full logits or standalone coding acceptance')
except BaseException as exc:
 error=exc;result.update(status='FAIL',error=dict(type=type(exc).__name__,message=str(exc)))
finally:
 if tunnel is not None:
  tunnel.terminate()
  try:tunnel.wait(timeout=10)
  except subprocess.TimeoutExpired:tunnel.kill();tunnel.wait(timeout=10)
 stop=['ssh','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','-o','HostKeyAlias=bw-llm60','-o','UserKnownHostsFile='+str(key/'known_hosts'),'-i',str(key/'id_ed25519'),'dflanag3@llm-60','stop-owned-campaign']
 try:
  p=subprocess.run(stop,capture_output=True,text=True,timeout=30)
  (b/'automatic-stop.json').write_text(json.dumps(dict(exit_code=p.returncode,stderr=p.stderr)))
  if p.returncode:raise RuntimeError('owned server stop request failed')
  for name in ['credentials.json','id_ed25519','id_ed25519.pub']:(key/name).unlink(missing_ok=True)
 except BaseException as exc:
  error=error or exc;result.update(status='FAIL',cleanup_error=dict(type=type(exc).__name__,message=str(exc)))
 result['whole_seconds']=time.monotonic()-start;save();finished.set();thread.join(timeout=1)
raise SystemExit(error is not None)
