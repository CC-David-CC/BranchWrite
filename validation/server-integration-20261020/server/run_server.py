import fcntl,os,runpy,sys
from pathlib import Path
os.umask(0o077);out=Path(__file__).resolve().parent
lock=open('/home/dflanag3/branching-g3/native-client-speed.gpu0.lock','a+')
fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
sys.argv=['serve.cow_http','--profile',str(out/'profile.json'),'--store',str(out/'store'),'--host','10.0.7.68','--port','18099','--text','--vision-config',str(out/'vision-config.json'),'--grammar-store',str(out/'grammars'),'--api-key',(out/'api-key.txt').read_text().strip(),'--ram-gib','24','--disk-gib','64','--checkpoint-idle-seconds','1800']
runpy.run_module('serve.cow_http',run_name='__main__')
