from pathlib import Path
import subprocess
b=Path(__file__).parent
with (b/'launch.stdout').open('x') as o,(b/'launch.stderr').open('x') as e:r=subprocess.run(['flock','-n','/home/dflanag3/branching-g3/native-client-speed.gpu0.lock','/home/dflanag3/src/Strata/.venv/bin/python','-B',str(b/'qualify.py')],stdout=o,stderr=e)
(b/'command.exit').write_text(str(r.returncode))
