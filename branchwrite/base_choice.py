"""Pure validation of model-proposed base choices, not execution or admission.

The host supplies catalog records and required identities. A model proposal is
untrusted data; this function only checks its shape and compatibility. It
returns a detached host record and the model's reason, granting nothing.
"""
import copy,json,re
from pathlib import Path

MAX_PROPOSAL_BYTES=65536
MAX_REASON_BYTES=2048
MAX_CATALOG_RECORDS=64
MAX_BRANCH_BYTES=128
_HEX64=re.compile('[0-9a-f]{64}')
_REVISION=re.compile('[0-9a-f]{40}|[0-9a-f]{64}')
_PROPOSAL_KEYS=frozenset(('schema','base_id','reason'))
_PACK_KEYS=frozenset(('reference_pack_path','reference_pack_id'))
_RECORD_KEYS=frozenset(('base_id','branch','snapshot','source_revision','execution_profile_id','prefix_tokens','capacity'))

def _pairs(rows):
 result={}
 for key,value in rows:
  if key in result:raise ValueError('duplicate base-proposal key')
  result[key]=value
 return result

def _constant(value):raise ValueError('nonfinite base-proposal value')

def _utf8_len(value,name):
 try:return len(value.encode('utf8'))
 except UnicodeEncodeError as exc:raise ValueError(name+' must be UTF-8 encodable') from exc

def _hex64(value,name):
 if type(value) is not str or _HEX64.fullmatch(value) is None:raise ValueError(name+' must be lowercase 64-hex')
 return value

def _revision(value,name):
 if type(value) is not str or _REVISION.fullmatch(value) is None:raise ValueError(name+' must be lowercase 40- or 64-hex')
 return value

def _count(value,name,*,minimum):
 if type(value) is not int or value<minimum:raise ValueError(name+' must be an exact integer at least '+str(minimum))
 return value

def _validate_catalog(catalog):
 if type(catalog) is not list or not 1<=len(catalog)<=MAX_CATALOG_RECORDS:raise ValueError('catalog must be a nonempty list of at most 64 records')
 seen=set()
 for row in catalog:
  if type(row) is not dict or set(row) not in (_RECORD_KEYS,_RECORD_KEYS|_PACK_KEYS):raise ValueError('catalog records have exactly the host base fields and optional complete reference-pack binding')
  if 'reference_pack_id' in row:
   _hex64(row['reference_pack_id'],'reference_pack_id')
   path=row['reference_pack_path']
   if type(path) is not str or _utf8_len(path,'reference_pack_path')>4096 or not Path(path).is_absolute():raise ValueError('reference_pack_path must be a bounded absolute path')
  base_id=_hex64(row['base_id'],'base_id')
  if base_id in seen:raise ValueError('duplicate catalog base_id')
  seen.add(base_id)
  branch=row['branch']
  if type(branch) is not str or not branch.strip() or _utf8_len(branch,'branch')>MAX_BRANCH_BYTES:raise ValueError('branch must be nonblank text of at most 128 UTF-8 bytes')
  _hex64(row['snapshot'],'snapshot')
  _revision(row['source_revision'],'source_revision')
  _hex64(row['execution_profile_id'],'execution_profile_id')
  prefix=_count(row['prefix_tokens'],'prefix_tokens',minimum=0)
  capacity=_count(row['capacity'],'capacity',minimum=1)
  if prefix>capacity:raise ValueError('prefix_tokens must not exceed capacity')

def resolve_base_proposal(text,catalog,*,required_revision,required_profile,reserve_tokens):
 """Return a detached compatible host base and model reason, or raise ValueError."""
 _revision(required_revision,'required_revision')
 _hex64(required_profile,'required_profile')
 if type(reserve_tokens) is not int or reserve_tokens<0:raise ValueError('reserve_tokens must be an exact nonnegative integer')
 _validate_catalog(catalog)
 if type(text) is not str or not text or _utf8_len(text,'proposal')>MAX_PROPOSAL_BYTES:raise ValueError('proposal requires nonempty text of at most 65536 UTF-8 bytes')
 try:proposal=json.loads(text,object_pairs_hook=_pairs,parse_constant=_constant)
 except (ValueError,RecursionError) as exc:raise ValueError('invalid base-proposal JSON') from exc
 if type(proposal) is not dict or set(proposal)!=_PROPOSAL_KEYS:raise ValueError('base proposal has exactly schema, base_id and reason')
 if type(proposal['schema']) is not int or proposal['schema']!=1:raise ValueError('base proposal schema must be integer 1')
 base_id=_hex64(proposal['base_id'],'base_id')
 reason=proposal['reason']
 if type(reason) is not str or not reason.strip() or _utf8_len(reason,'reason')>MAX_REASON_BYTES:raise ValueError('reason must be nonblank text of at most 2048 UTF-8 bytes')
 chosen=None
 for row in catalog:
  if row['base_id']==base_id:
   chosen=row
   break
 if chosen is None:raise ValueError('chosen base_id is not offered')
 if chosen['source_revision']!=required_revision or chosen['execution_profile_id']!=required_profile:raise ValueError('chosen base does not match required revision or profile')
 if chosen['prefix_tokens']+reserve_tokens>chosen['capacity']:raise ValueError('chosen base lacks capacity for reserve_tokens')
 _verify_reference_pack(chosen)
 return dict(base=copy.deepcopy(chosen),reason=reason)


def _verify_reference_pack(row):
 if 'reference_pack_id' in row:
  from .context_pack import load_verified_prefix
  load_verified_prefix(row['reference_pack_path'],expected_id=row['reference_pack_id'])


def select_host_base(catalog,*,required_revision,required_profile,reserve_tokens):
 """Choose among host-offered bases, not model summaries or live residency.

 Longest fitting prefix wins; exact base ID breaks ties independently of list
 order. The host is responsible for offering task-appropriate, current bases.
 Git revision compatibility alone does not establish working-tree freshness.
 """
 _revision(required_revision,'required_revision');_hex64(required_profile,'required_profile')
 if type(reserve_tokens) is not int or reserve_tokens<0:raise ValueError('reserve_tokens must be an exact nonnegative integer')
 _validate_catalog(catalog)
 pack_bound=any('reference_pack_id' in row for row in catalog)
 eligible=[row for row in catalog if (not pack_bound or 'reference_pack_id' in row) and row['source_revision']==required_revision
     and row['execution_profile_id']==required_profile
     and row['prefix_tokens']+reserve_tokens<=row['capacity']]
 from .context_pack import StalePackError
 fresh=[]
 for row in eligible:
  try:_verify_reference_pack(row)
  except StalePackError:continue
  fresh.append(row)
 eligible=fresh
 if not eligible:raise ValueError('no compatible Project Base satisfies revision, profile, token reserve and required pack freshness')
 chosen=min(eligible,key=lambda row:(-row['prefix_tokens'],row['base_id']))
 proposal=json.dumps(dict(schema=1,base_id=chosen['base_id'],reason='host-longest-fitting-v1: longest compatible offered prefix; base ID breaks ties'))
 return resolve_base_proposal(proposal,catalog,required_revision=required_revision,required_profile=required_profile,reserve_tokens=reserve_tokens)
