"""Exact bytes into an owned, content-addressed remote staging area.

This is a file receiver, not a workflow runtime. Publication into a live service
is a separate explicitly granted action. No root access or credential is needed.
"""
import hashlib,json,os,pwd,re,stat,sys,uuid
from pathlib import Path
MAX_UPLOAD=4*1024*1024

def store(home,name,digest,body):
 if (type(name) is not str or name in ('','.','..') or '/' in name or '\0' in name
     or len(name.encode('utf8'))>255 or type(digest) is not str
     or re.fullmatch('[0-9a-f]{64}',digest) is None or type(body) is not bytes
     or len(body)>MAX_UPLOAD or hashlib.sha256(body).hexdigest()!=digest):raise ValueError('invalid upload name, size or content hash')
 home=Path(home)
 if not home.is_absolute():raise ValueError('absolute target home required')
 flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW
 fd=os.open('/',flags)
 try:
  for part in home.parts[1:]:
   other=os.open(part,flags,dir_fd=fd);os.close(fd);fd=other
  def owned():
   i=os.fstat(fd)
   if i.st_uid!=os.getuid() or i.st_mode&0o022:raise ValueError('owned non-writable staging parent required')
  owned()
  for part in ('.branchwrite-uploads',digest):
   try:os.mkdir(part,0o700,dir_fd=fd)
   except FileExistsError:pass
   os.fsync(fd);other=os.open(part,flags,dir_fd=fd);os.close(fd);fd=other;owned()
  def verify():
   f=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
   try:
    i=os.fstat(f)
    if (not stat.S_ISREG(i.st_mode) or i.st_uid!=os.getuid() or i.st_nlink!=1
        or stat.S_IMODE(i.st_mode)!=0o400 or i.st_size!=len(body)):raise ValueError('existing upload is not the sealed original')
    actual=bytearray()
    while len(actual)<=MAX_UPLOAD:
     chunk=os.read(f,min(65536,MAX_UPLOAD+1-len(actual)))
     if not chunk:break
     actual.extend(chunk)
    if bytes(actual)!=body:raise ValueError('existing upload bytes differ')
    after=os.fstat(f)
    if (i.st_size,i.st_mtime_ns,i.st_ctime_ns)!=(after.st_size,after.st_mtime_ns,after.st_ctime_ns):raise ValueError('existing upload changed while checking')
    os.fsync(f)
   finally:os.close(f)
  try:verify()
  except FileNotFoundError:
   temp='.upload-'+uuid.uuid4().hex
   file=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o400,dir_fd=fd)
   try:
    with os.fdopen(file,'wb') as stream:stream.write(body);stream.flush();os.fsync(stream.fileno())
    try:os.link(temp,name,src_dir_fd=fd,dst_dir_fd=fd,follow_symlinks=False)
    except FileExistsError:pass
    os.unlink(temp,dir_fd=fd)
    verify()
   finally:
    try:os.unlink(temp,dir_fd=fd)
    except FileNotFoundError:pass
  os.fsync(fd)
 finally:os.close(fd)
 return dict(schema=1,remote_path=str(home/'.branchwrite-uploads'/digest/name),sha256=digest,bytes=len(body))

def main():
 if len(sys.argv)!=3:raise ValueError('filename and SHA256 required')
 body=sys.stdin.buffer.read(MAX_UPLOAD+1)
 value=store(Path(pwd.getpwuid(os.getuid()).pw_dir),sys.argv[1],sys.argv[2],body)
 sys.stdout.write(json.dumps(value,ensure_ascii=True,sort_keys=True));sys.stdout.flush()
if __name__=='__main__':main()
