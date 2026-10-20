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
  script='from branchwrite.tool_registry import ToolOutcome; from branchwrite.__main__ import main; import os,sys\noriginal=ToolOutcome.publish\ndef lost(self,log):\n if self.tool=="remote_command":os._exit(72)\n return original(self,log)\nToolOutcome.publish=lost\nraise SystemExit(main(sys.argv[1:]))\n'
  command=[str(out/'venv/bin/python'),'-c',script,*args]
 else:command=[str(exe),*args]
 f=subprocess.run(command,cwd=root,env=env,capture_output=True,text=True,timeout=30)
 count=len(list(root.glob('invoke-*.out')));(root/('invoke-'+str(count)+'.out')).write_text(f.stdout);(root/('invoke-'+str(count)+'.err')).write_text(f.stderr)
 return f

def record(label,case,result,expected):
 assert result.returncode==(0 if expected else 1),(label,result.returncode,result.stderr,result.stdout)
 report=json.loads(result.stdout);assert report['verified'] is expected,(label,report)
 rows.append(dict(id=label,status='PASS',verified=report['verified'],cli_exit=result.returncode,state=str(case[0]/'state')))
 (out/'workflow-result.json').write_text(json.dumps(dict(status='RUNNING',scope='installed CLI and real OS/SSH/VM, no model/GPU',rows=rows),indent=2)+'\n')
 return report

def simple(label,items,expected):
 case=prepare(label,items);return case,record(label,case,invoke(case),expected)

try:
 simple('RW01-remote-only-check',[proposal('check_remote',target='admin01',command='test "$(findmnt -n -o SOURCE /)" = /dev/vda2')],True)
 simple('RW02-action-without-check',[proposal('remote_command',target='admin01',command='true')],False)
 simple('RW03-failing-remote-check',[proposal('check_remote',target='admin01',command='exit 7')],False)
 simple('RW04-later-action-stales-check',[proposal('check_remote',target='admin01',command='true'),proposal('remote_command',target='admin01',command='true')],False)
 simple('RW05-local-edit-still-needs-local-check',[proposal('create_file',path='index.html',content='<h1>saved file</h1>'),proposal('check_remote',target='admin01',command='true')],False)
 simple('RW06-local-and-remote-evidence',[proposal('create_file',path='index.html',content='<h1>saved file</h1>'),proposal('run_check',name='created_file',command='test -f index.html'),proposal('check_remote',target='admin01',command='true')],True)
 simple('RW07-latest-remote-failure',[proposal('check_remote',target='admin01',command='true'),proposal('check_remote',target='admin01',command='exit 4')],False)
 simple('RW08-repaired-remote-check',[proposal('check_remote',target='admin01',command='exit 4'),proposal('check_remote',target='admin01',command='true')],True)
 peer=prepare('RW09-other-client-invalidates-check',[proposal('check_remote',target='admin01',command='true')])
 found=False
 for n in range(16):
  f=invoke(peer,steps=1);assert f.returncode in (0,1,3),(f.returncode,f.stderr)
  with RuntimeLog(peer[0]/'state/ledger',read_only=True) as log:
   for frame in FrameKernel(log).frames():
    if frame['contract']==('ToolOutcome','record') and frame['state']=='Closed':
     value=decode(log.read_artifact(Artifact(*frame['result'])))[2]
     if value['tool']=='check_remote':found=True
  if found:break
 assert found,'first client never reached a closed remote check'
 simple('RW09-peer-mutation',[proposal('remote_command',target='admin01',command='true')],False)
 record('RW09-other-client-invalidates-check',peer,invoke(peer),False)
 marker='/home/maint/.local/share/bw-kernel-return-'+nonce
 case=prepare('RW10-lost-local-return',[proposal('remote_command',target='admin01',command="printf 'once\\n' >> "+marker),proposal('check_remote',target='admin01',command='test "$(grep -cx once '+marker+')" = 1')])
 f=invoke(case,crash=True);assert f.returncode==72,(f.returncode,f.stderr)
 with RuntimeLog(case[0]/'state/ledger',read_only=True) as log:
  calls=[x for x in FrameKernel(log).frames() if x['contract']==('ToolOutcome','record') and x['state']=='Waiting'];assert len(calls)==1
  operation=calls[0]['dispatch'][0]
 record('RW10-lost-local-return',case,invoke(case),True)
 with RuntimeLog(case[0]/'state/ledger',read_only=True) as log:
  matched=[x for x in FrameKernel(log).frames() if x['contract']==('ToolOutcome','record') and x['dispatch'] and x['dispatch'][0]==operation];assert len(matched)==1 and matched[0]['state']=='Closed'
  outcome=decode(log.read_artifact(Artifact(*matched[0]['result'])))[2];assert outcome['operation_id']==operation
 rows[-1].update(original_operation_id=operation,client_crash_exit=72,same_frame_settled=True,guest_append_count=1)
 result=dict(status='PASS',scope='installed CLI/Interpreter/Kernel/real SSH/owned persistent VM, no model/GPU',rows=rows,source_wheel_sha256=hashlib.sha256((out/'branchwrite-0.1.0.dev49-py3-none-any.whl').read_bytes()).hexdigest())
except BaseException as error:
 import traceback
 result=dict(status='FAIL',rows=rows,error=repr(error),traceback=traceback.format_exc());raise
finally:(out/'workflow-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'}));print('completed_cases',len(rows))
