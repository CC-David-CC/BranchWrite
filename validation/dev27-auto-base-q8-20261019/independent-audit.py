"""Parent-operated acceptance after both client producers terminate."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib,json,re,os
from branchwrite.execution import Executor,Grant
from branchwrite.terminal import ShellConfig
D=Path(__file__).parent
assert (D/'result.json').exists(), 'Campaign must finish before independent audit'
for name in ('first','second'):
 pid=int((D/(name+'.pid')).read_text())
 assert not Path('/proc',str(pid)).exists(), 'Do not inspect a live producer'
class Text(HTMLParser):
 def __init__(self):super().__init__();self.parts=[]
 def handle_data(self,text):self.parts.append(text)
checks={}
for name in ('first','second'):
 workspace=D/('state-'+name)/'world/workspace'
 assert (workspace/'check_site.py').read_bytes()==(D/'source-first/check_site.py').read_bytes()
 executor=Executor.create(workspace,D/('independent-'+name),shell=ShellConfig(timeout=5))
 grant=Grant((),False,read_paths=('index.html','style.css','check_site.py'),allow_shell=True)
 result=executor.run_shell('independent-check',grant,'python3 check_site.py')
 assert result.exit_code==0,result.stderr.read_bytes()
 page=Text();page.feed((workspace/'index.html').read_text());text=' '.join(' '.join(page.parts).lower().split())
 assert 'garden' in text
 if name=='second':
  assert 'meeting' in text and 'saturday' in text and re.search(r'10\s*(?::\s*00\s*)?a\.?m',text),text
 checks[name]=dict(structural_exit=result.exit_code,stdout=result.stdout.read_bytes().decode(),isolation=result.details['isolation'],files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in workspace.iterdir() if p.is_file()})
launch=json.loads((D/'state-second/coding-launch.json').read_text())['launch']
choice=json.loads(launch['config']['bindings']['project_base_choice']['value'])
assert choice['base']['snapshot']==json.loads((D/'base-before.json').read_text())['root']
assert choice['base']['prefix_tokens']==json.loads((D/'root-measurement.json').read_text())['consumed']
result=dict(status='PASS',scope='Independent structural checks and requested meeting content; no visual or numerical oracle',checks=checks,choice=choice)
(D/'independent-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
