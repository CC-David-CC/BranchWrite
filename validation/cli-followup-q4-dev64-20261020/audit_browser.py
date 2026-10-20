from pathlib import Path
import json,hashlib
from branchwrite.browser_capture import BrowserConfig,PageInspection,render_snapshot
root=Path(__file__).parent;record=json.loads((root/'resume-result.json').read_text())
assert record['status']=='CLIENT_PASS_PENDING_INDEPENDENT_BROWSER' and record['client_exit']==0
source=Path(record['workspace'])/'index.html';raw=source.read_bytes();record['html_sha256']=hashlib.sha256(raw).hexdigest()
checker=root/'website_checks.py';inspection=PageInspection(checker,hashlib.sha256(checker.read_bytes()).hexdigest(),'custom')
chrome=Path('/home/dflanag3/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome')
rows=[]
for name,width,height in [('desktop',1280,800),('phone',375,812)]:
 result=render_snapshot(raw,BrowserConfig(chrome,width,height,30,inspection=inspection))
 (root/('followup-'+name+'.png')).write_bytes(result.png)
 row=dict(viewport=name,width=width,height=height,inspection=result.inspection,runtime_errors=result.runtime_errors,served_sha256=result.served_sha256,isolation=result.isolation)
 rows.append(row)
 assert result.inspection['status']=='PASS' and not result.runtime_errors,row
 assert result.served_sha256==record['html_sha256'],row
report=dict(status='BROWSER_CHECKS_PASS_PENDING_VISUAL_REVIEW',html_sha256=record['html_sha256'],actual_checks=rows,scope='actual isolated Chromium desktop/phone, blue h1, button causes visible greeting, no overflow/no JS or external resources, exact served source; actual bold names, italic+underlined Welcome, unchanged wording; visuals reviewed separately')
(root/'browser-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='actual_checks'}))
