from pathlib import Path
import subprocess
b=Path(__file__).parent
with (b/'client.stdout').open('x') as out,(b/'client.stderr').open('x') as err:
 p=subprocess.run(['/home/dflanag3/spatial-artifacts/branchwrite-dev16-package-20261019-v1/installation/venv/bin/python','-I','-B',str(b/'run-diagnostic.py')],cwd=b,stdin=subprocess.DEVNULL,stdout=out,stderr=err)
(b/'command.exit').write_text(str(p.returncode))
