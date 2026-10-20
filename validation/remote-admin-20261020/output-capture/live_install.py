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
 f=subprocess.run(command,cwd=root,env=env,capture_output=True,text=True,timeout=330)
 count=len(list(root.glob('invoke-*.out')));(root/('invoke-'+str(count)+'.out')).write_text(f.stdout);(root/('invoke-'+str(count)+'.err')).write_text(f.stderr)
 return f

def record(label,case,result,expected):
 assert result.returncode==(0 if expected else 1),(label,result.returncode,result.stderr,result.stdout)
 report=json.loads(result.stdout);assert report['verified'] is expected,(label,report)
 rows.append(dict(id=label,status='PASS',verified=report['verified'],cli_exit=result.returncode,state=str(case[0]/'state')))
 (out/'installation-progress.json').write_text(json.dumps(dict(status='RUNNING',scope='installed CLI and real OS/SSH/VM, no model/GPU',rows=rows),indent=2)+'\n')
 return report

def simple(label,items,expected):
 case=prepare(label,items);return case,record(label,case,invoke(case),expected)

remote['timeout']=300
try:
 simple('RI01-large-real-file-write',[
  proposal('remote_command',target='admin01',command="set -e; mkdir -p /home/maint/.local/share/bw-capture-proof; dd if=/dev/zero of=/home/maint/.local/share/bw-capture-proof/large-file bs=1048576 count=2 status=none"),
  proposal('check_remote',target='admin01',command="test $(stat -c %s /home/maint/.local/share/bw-capture-proof/large-file) = 2097152")],True)
 # This is the owned VM and the welcome service created by the preceding model
 # pilot. Its recorded result remains intact; this test replaces it with nginx.
 simple('RI02-real-package-install',[
  proposal('remote_command',target='admin01',command="set -e; grep -Fq 'BranchWrite welcome web server' /etc/systemd/system/welcome-web.service; sudo -n systemctl stop welcome-web; sudo -n env DEBIAN_FRONTEND=noninteractive apt-get update; sudo -n env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends nginx; sudo -n systemctl enable --now nginx"),
  proposal('check_remote',target='admin01',command="set -e; sudo -n nginx -t; test $(systemctl is-active nginx) = active; test $(systemctl is-enabled nginx) = enabled; curl -fsS http://127.0.0.1/ | grep -Fi 'nginx'")],True)
 result=dict(status='PASS',rows=rows,scope='installed CLI to real SSH/VM package installation; operator-specified workflow, not autonomous model evidence')
except BaseException as error:
 import traceback
 result=dict(status='FAIL',rows=rows,error=repr(error),traceback=traceback.format_exc());raise
finally:
 (out/'installation-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
