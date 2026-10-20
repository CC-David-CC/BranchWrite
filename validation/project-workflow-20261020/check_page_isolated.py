from pathlib import Path
import json,hashlib
from branchwrite.browser_capture import BrowserConfig,PageAction,render_snapshot
out=Path(__file__).resolve().parent
payload=(out/'generated-index.html').read_bytes()
rows=[]
for width,height in [(1280,800),(375,812)]:
 cfg=BrowserConfig(Path('/home/dflanag3/spatial-artifacts/branchwrite-mode-tool-20261019-v1/browser/chromium-1248/chrome-linux64/chrome'),width,height,actions=(PageAction('click','hello-button'),))
 result=render_snapshot(payload,cfg)
 assert 'Hello, David!' in result.text,result.text
 assert not result.runtime_errors,result.runtime_errors
 assert result.isolation['chromium_sandbox'] is True
 assert result.isolation['worker_exited'] is True
 assert result.isolation['namespace_members_after']==[]
 image=out/('website-'+str(width)+'.png');image.write_bytes(result.png)
 rows.append(dict(viewport=[width,height],status='PASS',text=result.text,actions=result.actions,isolation=result.isolation,screenshot=str(image)))
report=dict(status='PASS',source_sha256=hashlib.sha256(payload).hexdigest(),checks=rows,scope='Actual isolated Chromium click and visible text at desktop/mobile sizes; screenshots retained. Not a browser feature matrix.')
(out/'page-result.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
