import hashlib,json,time
from pathlib import Path
from branchwrite.browser_capture import BrowserConfig,PageInspection,render_snapshot
r=Path(__file__).parent;rows=[]
for label,color in [('work','blue'),('edit','purple'),('explore','green')]:
 if not (r/(label+'.html')).exists():continue
 page=(r/(label+'.html')).read_bytes();checks=r/('checks-'+label+'.py')
 checks.write_text('EXPECTED='+repr(color)+'\n'+(r/'checks.py').read_text())
 for width,height in [(1280,800),(375,812)]:
  result=render_snapshot(page,BrowserConfig(Path('/home/dflanag3/spatial-artifacts/branchwrite-mode-tool-20261019-v1/browser/chromium-1248/chrome-linux64/chrome'),width,height,inspection=PageInspection(checks,hashlib.sha256(checks.read_bytes()).hexdigest(),'custom')))
  image=r/(label+'-'+str(width)+'.png');image.write_bytes(result.png)
  row=dict(label=label,color=color,viewport=[width,height],inspection=result.inspection,isolation=result.isolation,runtime_errors=result.runtime_errors,source_sha256=result.served_sha256,screenshot=str(image));rows.append(row)
  report=dict(status='PASS' if all(v['inspection']['status']=='PASS' and not v['runtime_errors'] for v in rows) else 'FAIL',rows=rows)
  (r/'result.json').write_text(json.dumps(report,indent=2)+'\n')
  if report['status']!='PASS':raise AssertionError(row)
print(json.dumps(dict(status=report['status'],viewports=len(rows),cases=sorted({row['label'] for row in rows}))))
