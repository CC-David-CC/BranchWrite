import hashlib,json
from pathlib import Path
from branchwrite.browser_capture import BrowserConfig,PageInspection,render_snapshot
r=Path(__file__).parent;checks=r/'checks.py';page=(r/'resumed.html').read_bytes();rows=[]
for width,height in [(1280,800),(375,812)]:
 result=render_snapshot(page,BrowserConfig(Path('/home/dflanag3/spatial-artifacts/branchwrite-mode-tool-20261019-v1/browser/chromium-1248/chrome-linux64/chrome'),width,height,inspection=PageInspection(checks,hashlib.sha256(checks.read_bytes()).hexdigest(),'custom')))
 image=r/('resumed-'+str(width)+'.png');image.write_bytes(result.png)
 rows.append(dict(viewport=[width,height],inspection=result.inspection,isolation=result.isolation,runtime_errors=result.runtime_errors,source_sha256=result.served_sha256,screenshot=str(image)))
 report=dict(status='PASS' if all(v['inspection']['status']=='PASS' and not v['runtime_errors'] for v in rows) else 'FAIL',rows=rows)
 (r/'result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
assert report['status']=='PASS'
