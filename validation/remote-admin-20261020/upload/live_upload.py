import hashlib,json,os,socket,subprocess,sys,time,uuid
from pathlib import Path
from branchwrite.records import RuntimeLog,Artifact,decode
from branchwrite.kernel import FrameKernel
out=Path(__file__).parent;vm=Path('/home/dflanag3/.local/share/bw-vm/admin01');exe=out/'venv/bin/branchwrite';nonce=uuid.uuid4().hex[:10];rows=[]
env=os.environ.copy();env.pop('PYTHONPATH',None)
remote=dict(host='127.0.0.1',port=22220,user='maint',identity_file=str(vm/'guest-key'),known_hosts_file=str(vm/'known_hosts-a432129ef6d1'),timeout=30,owner_hostname=socket.gethostname())
def proposal(tool,**arguments):return dict(tool=tool,arguments=arguments)
def prepare(label,items):
 root=out/(label+'-'+nonce);root.mkdir(mode=0o700);project=root/'project';project.mkdir();program=root/'workflow.bw';config=root/'config.json';bindings={};text='FLOW remote\n'
 for i,item in enumerate(items):
  key='p'+str(i);bindings[key]=dict(type='ToolProposal',value=json.dumps(item));text+='PLAN f'+str(i)+' from='+key+' against=world -> plan\nACT a'+str(i)+' plan=plan -> result\n'
 bindings['finish']=dict(type='ToolProposal',value=json.dumps(proposal('finish',answer='Selected checks completed.')))
 text+='PLAN final from=finish against=world -> plan\nACT done plan=plan -> outcome\nVERIFY verify input=outcome contract=project-checks-and-finish -> verified\nEND\n'
 program.write_text(text);config.write_text(json.dumps(dict(schema=1,source=str(project),run_id=label+'-'+nonce,grant=dict(read_paths=[],edit_paths=[],create_paths=[],allow_tests=False,allow_shell=True,project_files=True,remote_targets=['admin01']),remotes=dict(admin01=remote),shell=dict(timeout=10),verification=dict(schema=1,selected_checks=True),bindings=bindings)));config.chmod(0o600)
 return root,program,config

def invoke(case,*,steps=1024,crash=False):
 root,program,config=case;args=['run',str(program),'--config',str(config),'--state',str(root/'state'),'--max-steps',str(steps)]
 if crash:
  script='from branchwrite.tool_registry import ToolOutcome; from branchwrite.__main__ import main; import os,sys\noriginal=ToolOutcome.publish\ndef lost(self,log):\n if self.tool=="upload_file":os._exit(72)\n return original(self,log)\nToolOutcome.publish=lost\nraise SystemExit(main(sys.argv[1:]))\n'
  command=[str(out/'venv/bin/python'),'-c',script,*args]
 else:command=[str(exe),*args]
 f=subprocess.run(command,cwd=root,env=env,capture_output=True,text=True,timeout=30)
 count=len(list(root.glob('invoke-*.out')));(root/('invoke-'+str(count)+'.out')).write_text(f.stdout);(root/('invoke-'+str(count)+'.err')).write_text(f.stderr)
 return f

def record(label,case,result,expected):
 assert result.returncode==(0 if expected else 1),(label,result.returncode,result.stderr,result.stdout)
 report=json.loads(result.stdout);assert report['verified'] is expected,(label,report)
 rows.append(dict(id=label,status='PASS',verified=report['verified'],cli_exit=result.returncode,state=str(case[0]/'state')))
 (out/'upload-progress.json').write_text(json.dumps(dict(status='RUNNING',scope='installed CLI and real OS/SSH/VM, no model/GPU',rows=rows),indent=2)+'\n')
 return report

def simple(label,items,expected):
 case=prepare(label,items);return case,record(label,case,invoke(case),expected)

import shlex

def upload_case(label,body,name):
 digest=hashlib.sha256(body).hexdigest();path='/home/maint/.branchwrite-uploads/'+digest+'/'+name
 items=[proposal('upload_file',target='admin01',path=name),proposal('check_remote',target='admin01',command='test "$(sha256sum '+shlex.quote(path)+' | cut -d " " -f 1)" = '+digest)]
 case=prepare(label,items);(case[0]/'project'/name).write_bytes(body)
 return case,path,digest

try:
 case,path,digest=upload_case('RU01-small-unicode',b'<h1>exact bytes</h1>\r\n',"caf\u00e9 $HOME 'quoted'.html")
 record('RU01-small-unicode',case,invoke(case),True)
 case,path,digest=upload_case('RU02-two-megabytes',bytes(range(256))*8192,'large.bin')
 record('RU02-two-megabytes',case,invoke(case),True)
 case,path,digest=upload_case('RU03-original-upload-receipt',b'recover upload without resending\n','recover.txt')
 failed=invoke(case,crash=True);assert failed.returncode==72,(failed.returncode,failed.stderr)
 with RuntimeLog(case[0]/'state/ledger',read_only=True) as log:
  pending=[v for v in FrameKernel(log).frames() if v['contract']==('ToolOutcome','record') and v['state']=='Waiting'];assert len(pending)==1
  original=pending[0]['dispatch'][0]
 # The new client is forbidden to resend that original native SSH operation.
 script='from branchwrite.remote_execution import RemoteTransport; from branchwrite.__main__ import main; import sys\nold=RemoteTransport._send\ndef guarded(self,intent,args):\n if intent["operation_id"]=='+repr(original)+':raise AssertionError("original upload was resent")\n return old(self,intent,args)\nRemoteTransport._send=guarded\nraise SystemExit(main(sys.argv[1:]))\n'
 command=[str(out/'venv/bin/python'),'-c',script,'run',str(case[1]),'--config',str(case[2]),'--state',str(case[0]/'state')]
 recovered=subprocess.run(command,cwd=case[0],env=env,capture_output=True,text=True,timeout=30)
 (case[0]/'recovery.stdout').write_text(recovered.stdout);(case[0]/'recovery.stderr').write_text(recovered.stderr)
 record('RU03-original-upload-receipt',case,recovered,True)
 rows[-1].update(original_operation_id=original,original_resend_forbidden=True,client_crash_exit=72)
 with RuntimeLog(case[0]/'state/ledger',read_only=True) as log:
  calls=[v for v in FrameKernel(log).frames() if v['contract']==('ToolOutcome','record') and v['dispatch'] and v['dispatch'][0]==original];assert len(calls)==1 and calls[0]['state']=='Closed'
 result=dict(status='PASS',rows=rows,scope='installed CLI/Kernel real SSH/VM exact upload and original-receipt recovery, no model inference',wheel_sha256=hashlib.sha256((out/'branchwrite-0.1.0.dev51-py3-none-any.whl').read_bytes()).hexdigest())
except BaseException as error:
 import traceback
 result=dict(status='FAIL',rows=rows,error=repr(error),traceback=traceback.format_exc());raise
finally:
 (out/'upload-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
