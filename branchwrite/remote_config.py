"""Explicit operator remote capabilities; credentials stay outside project worlds."""
import json,os,socket
from pathlib import Path
from .remote_execution import RemoteTarget,validate_target_fields,_private

_FIELDS={'host','port','user','identity_file','known_hosts_file','timeout','owner_hostname'}
def validate_targets(spec):
 if type(spec) is not dict or len(spec)>32:raise ValueError('bounded named remote target mapping required')
 for name,value in spec.items():
  if type(value) is not dict or set(value)!=_FIELDS:raise ValueError('closed remote target configuration required')
  if any(type(value[k]) is not str for k in ('identity_file','known_hosts_file')):raise ValueError('absolute credential references required')
  owner=value['owner_hostname']
  if type(owner) is not str or not owner or len(owner)>255 or any(ord(c)<33 or ord(c)>126 for c in owner):raise ValueError('exact client hostname required')
  validate_target_fields(name,**{k:value[k] for k in _FIELDS-{'owner_hostname'}})
 return json.loads(json.dumps(spec,allow_nan=False))

def load_targets(spec):
 spec=validate_targets(spec);targets=[]
 for name,value in spec.items():
  if value['owner_hostname']!=socket.gethostname():raise ValueError('Remote capability belongs to client '+value['owner_hostname'])
  targets.append(RemoteTarget(name,**{k:value[k] for k in _FIELDS-{'owner_hostname'}}))
 return tuple(targets)

def load_file(path):
 def pairs(items):
  value={}
  for key,item in items:
   if key in value:raise ValueError('duplicate remote configuration field')
   value[key]=item
  return value
 value=json.loads(_private(Path(path)),object_pairs_hook=pairs)
 if type(value) is not dict or set(value)!={'schema','targets'} or type(value['schema']) is not int or value['schema']!=1:raise ValueError('remote target file requires schema1 and targets')
 return validate_targets(value['targets'])

def client_targets(*,environ=None,home=None):
 env=os.environ if environ is None else environ;home=Path.home() if home is None else Path(home)
 explicit=env.get('BW_REMOTE_TARGETS');path=Path(explicit) if explicit else home/'.config/branchwrite/remote-targets.json'
 if not path.exists() and not path.is_symlink():
  if explicit:raise ValueError('Selected remote target file is missing')
  return {}
 spec=load_file(path)
 if any(v['owner_hostname']!=socket.gethostname() for v in spec.values()):raise ValueError('Remote target configuration belongs to another client')
 return spec
