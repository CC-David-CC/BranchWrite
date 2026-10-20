from pathlib import Path
import os,json,hashlib,subprocess,time
root=Path(__file__).parent;d=root/'coding-comparison-service';a=Path.home()/'.ssh/authorized_keys'
assert not (d/'owned-key-added').exists()
prep=json.loads((root/'native-base-preparation-v4.json').read_text());assert prep['status']=='PASS' and len(prep['bases'])==3
pub=(root/'client-public-key.txt').read_text().strip();assert pub.startswith('ssh-ed25519 ') and len(pub.split())==3
added=('restrict,port-forwarding,permitopen="127.0.0.1:*",command="/bin/false" '+pub+'\n').encode()
raw=a.read_bytes();assert pub.encode() not in raw
(d/'authorized-keys-before.sha256').write_text(hashlib.sha256(raw).hexdigest())
(d/'owned-key-added').write_bytes(added);(d/'owned-key-added').chmod(0o600)
# Retire only our exact line, preserving independently added keys.
retire=d/'retire-owned-key.py'
retire.write_text('from pathlib import Path\nimport json,time,hashlib,os\nb=Path(__file__).parent\na=Path.home()/".ssh/authorized_keys"\nwhile not (b/"command.exit").exists():time.sleep(1)\nraw=a.read_bytes();added=(b/"owned-key-added").read_bytes();assert raw.count(added)==1\nnew=raw.replace(added,b"",1);tmp=a.with_name("authorized_keys.project-base-cleanup")\nfd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)\nwith os.fdopen(fd,"wb") as f:f.write(new);f.flush();os.fsync(f.fileno())\nassert a.read_bytes()==raw;os.replace(tmp,a)\n(b/"ssh-cleanup.json").write_text(json.dumps(dict(owned_key_revoked=True,original_keys_byte_exact=hashlib.sha256(new).hexdigest()==(b/"authorized-keys-before.sha256").read_text().strip())))\n')
tmp=a.with_name('authorized_keys.project-base-install');fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'wb') as f:f.write(raw+(b'' if not raw or raw.endswith(b'\n') else b'\n')+added);f.flush();os.fsync(f.fileno())
assert a.read_bytes()==raw;os.replace(tmp,a)
with (d/'retire.stdout').open('x') as o,(d/'retire.stderr').open('x') as e:
 child=subprocess.Popen(['/usr/bin/python3','-B',str(retire)],stdin=subprocess.DEVNULL,stdout=o,stderr=e,start_new_session=True)
(d/'retire.pid').write_text(str(child.pid));print('restricted forwarding key installed; cleanup watcher',child.pid)
