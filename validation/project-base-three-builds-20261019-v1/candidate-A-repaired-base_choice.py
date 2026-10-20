"""Pure validation of model-proposed base choices, not selection authority.

The host supplies catalog and requirements; model text is untrusted data.
This module only validates and detaches one chosen host record.
"""
import copy,json,math,re

MAX_PROPOSAL_BYTES=65536
MAX_REASON_BYTES=2048
MAX_BRANCH_BYTES=128
MAX_CATALOG=64
_HEX64=re.compile(r'[0-9a-f]{64}\Z')
_REVISION=re.compile(r'(?:[0-9a-f]{40}|[0-9a-f]{64})\Z')
_FIELDS=frozenset(('base_id','branch','snapshot','source_revision','execution_profile_id','prefix_tokens','capacity'))

def _pairs(rows):
 result={}
 for key,value in rows:
  if key in result:raise ValueError('duplicate proposal key')
  result[key]=value
 return result

def _constant(value):raise ValueError('nonfinite proposal value')

def _finite(value):
 stack=[value]
 while stack:
  item=stack.pop()
  if type(item) is float:
   if not math.isfinite(item):raise ValueError('nonfinite proposal value')
  elif type(item) is dict:
   stack.extend(item.values())
  elif type(item) is list:
   stack.extend(item)

def _text(value,name,limit,*,blank=False):
 if type(value) is not str:raise ValueError(name+' must be text')
 try:size=len(value.encode('utf8'))
 except UnicodeEncodeError as exc:raise ValueError(name+' is not encodable UTF-8') from exc
 if size>limit:raise ValueError(name+' exceeds byte bound')
 if blank and not value.strip():raise ValueError(name+' must be nonblank')
 return value

def _hex64(value,name):
 if type(value) is not str or _HEX64.fullmatch(value) is None:raise ValueError(name+' must be lowercase 64-hex')
 return value

def _revision(value,name):
 if type(value) is not str or _REVISION.fullmatch(value) is None:raise ValueError(name+' must be lowercase 40 or 64 hex')
 return value

def _count(value,name,*,minimum):
 if type(value) is not int:raise ValueError(name+' must be an exact integer')
 if value<minimum:raise ValueError(name+' is below its bound')
 return value

def _validate_catalog(catalog):
 if type(catalog) is not list or not 1<=len(catalog)<=MAX_CATALOG:raise ValueError('catalog must be a nonempty list of at most 64 records')
 seen=set();records=[]
 for row in catalog:
  if type(row) is not dict or set(row)!=_FIELDS:raise ValueError('catalog record has unexpected fields')
  base_id=_hex64(row['base_id'],'base_id')
  branch=_text(row['branch'],'branch',MAX_BRANCH_BYTES,blank=True)
  snapshot=_hex64(row['snapshot'],'snapshot')
  revision=_revision(row['source_revision'],'source_revision')
  profile=_hex64(row['execution_profile_id'],'execution_profile_id')
  prefix=_count(row['prefix_tokens'],'prefix_tokens',minimum=0)
  capacity=_count(row['capacity'],'capacity',minimum=1)
  if prefix>capacity:raise ValueError('prefix_tokens exceeds capacity')
  if base_id in seen:raise ValueError('duplicate catalog base_id')
  seen.add(base_id)
  records.append(row)
 return records

def resolve_base_proposal(text,catalog,*,required_revision,required_profile,reserve_tokens):
 if type(text) is not str:raise ValueError('proposal must be text')
 try:proposal_bytes=len(text.encode('utf8'))
 except UnicodeEncodeError as exc:raise ValueError('proposal is not encodable UTF-8') from exc
 if not 0<proposal_bytes<=MAX_PROPOSAL_BYTES:raise ValueError('proposal requires bounded nonempty UTF-8 text')
 try:proposal=json.loads(text,object_pairs_hook=_pairs,parse_constant=_constant)
 except (ValueError,TypeError,RecursionError) as exc:raise ValueError('invalid base proposal JSON') from exc
 _finite(proposal)
 if type(proposal) is not dict or set(proposal)!={'schema','base_id','reason'}:raise ValueError('proposal fields are schema, base_id, reason only')
 if type(proposal['schema']) is not int or proposal['schema']!=1:raise ValueError('proposal schema must be integer 1')
 base_id=_hex64(proposal['base_id'],'base_id')
 reason=_text(proposal['reason'],'reason',MAX_REASON_BYTES,blank=True)
 required_revision=_revision(required_revision,'required_revision')
 required_profile=_hex64(required_profile,'required_profile')
 reserve_tokens=_count(reserve_tokens,'reserve_tokens',minimum=0)
 records=_validate_catalog(catalog)
 chosen=next((row for row in records if row['base_id']==base_id),None)
 if chosen is None:raise ValueError('chosen base_id is not offered')
 if chosen['source_revision']!=required_revision:raise ValueError('chosen base source_revision differs from requirement')
 if chosen['execution_profile_id']!=required_profile:raise ValueError('chosen base execution_profile_id differs from requirement')
 if chosen['prefix_tokens']+reserve_tokens>chosen['capacity']:raise ValueError('chosen base lacks capacity for reserve_tokens')
 return dict(base=copy.deepcopy(chosen),reason=reason)
