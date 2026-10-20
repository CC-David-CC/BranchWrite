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
 (out/'feedback-progress.json').write_text(json.dumps(dict(status='RUNNING',scope='installed CLI and real OS/SSH/VM, no model/GPU',rows=rows),indent=2)+'\n')
 return report

def simple(label,items,expected):
 case=prepare(label,items);return case,record(label,case,invoke(case),expected)

try:
 case=prepare('VF01-stale-local-check',[
  proposal('create_file',path='index.html',content='<h1>first</h1>'),
  proposal('run_check',name='site',command='test -f index.html'),
  proposal('create_file',path='other.txt',content='new file changes inventory')])
 root,program,config=case
 text=program.read_text().replace('END\n','TRANSFORM feedback input=outcome contract=tool-feedback evidence=verified -> feedback\nEND\n');program.write_text(text)
 record('VF01-stale-local-check',case,invoke(case),False)
 with RuntimeLog(root/'state/ledger',read_only=True) as log:
  frame=FrameKernel(log).frame('program');value=decode(log.read_artifact(Artifact(*frame['result'])))[2]
  feedback=json.loads(value['bindings']['feedback'][1]);assert feedback['verification']['status']=='fail'
  assert feedback['verification']['checks'][0]['name']=='site'
  assert feedback['verification']['checks'][0]['exit_code']==0
  assert feedback['verification']['checks'][0]['status']=='fail'
  assert feedback['verification']['outcome_operation_id']==feedback['operation_id']
 (out/'recorded-feedback.json').write_text(json.dumps(feedback,indent=2)+'\n')
 case=prepare('VF02-repaired-local-check',[
  proposal('create_file',path='index.html',content='<h1>first</h1>'),
  proposal('run_check',name='site',command='test -f index.html'),
  proposal('create_file',path='other.txt',content='new file changes inventory'),
  proposal('run_check',name='site',command='test -f index.html && test -f other.txt')])
 root,program,config=case;program.write_text(program.read_text().replace('END\n','TRANSFORM feedback input=outcome contract=tool-feedback evidence=verified -> feedback\nEND\n'))
 record('VF02-repaired-local-check',case,invoke(case),True)
 result=dict(status='PASS',rows=rows,scope='installed CLI, actual local shell checks and recorded typed feedback; no GPU or remote effects')
except BaseException as error:
 import traceback
 result=dict(status='FAIL',rows=rows,error=repr(error),traceback=traceback.format_exc());raise
finally:
 (out/'feedback-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
