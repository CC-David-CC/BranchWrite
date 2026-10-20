"""Pure validation of model-proposed base selection, not execution or granting.

The host supplies catalog records and required identities. A model proposal is
untrusted data; this function only checks its shape and compatibility.
"""
import copy,json,re

MAX_PROPOSAL_BYTES=65536
MAX_REASON_BYTES=2048
MAX_CATALOG_RECORDS=64
MAX_BRANCH_BYTES=128
_HEX64=re.compile(r"[0-9a-f]{64}")
_REVISION=re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
_PROPOSAL_KEYS=frozenset(("schema","base_id","reason"))
_RECORD_KEYS=frozenset(("base_id","branch","snapshot","source_revision","execution_profile_id","prefix_tokens","capacity"))

def _pairs(rows):
 result={}
 for key,value in rows:
  if key in result:raise ValueError("duplicate base-proposal key")
  result[key]=value
 return result

def _constant(value):raise ValueError("nonfinite base-proposal value")

def _utf8_length(value):
 try:return len(value.encode("utf8"))
 except UnicodeEncodeError as exc:raise ValueError("text must be UTF-8 encodable") from exc

def _exact_int(value):return type(value) is int

def _hex64(value):return type(value) is str and _HEX64.fullmatch(value) is not None

def _revision(value):return type(value) is str and _REVISION.fullmatch(value) is not None

def _branch(value):return type(value) is str and bool(value.strip()) and _utf8_length(value)<=MAX_BRANCH_BYTES

def _validate_catalog(catalog):
 if type(catalog) is not list or not 1<=len(catalog)<=MAX_CATALOG_RECORDS:
  raise ValueError("catalog must be a nonempty list of at most 64 records")
 by_id={}
 for row in catalog:
  if type(row) is not dict or set(row)!=_RECORD_KEYS:
   raise ValueError("catalog record fields are base_id, branch, snapshot, source_revision, execution_profile_id, prefix_tokens, capacity only")
  base_id=row["base_id"]
  branch=row["branch"]
  snapshot=row["snapshot"]
  source_revision=row["source_revision"]
  execution_profile_id=row["execution_profile_id"]
  prefix_tokens=row["prefix_tokens"]
  capacity=row["capacity"]
  if not _hex64(base_id) or not _hex64(snapshot) or not _revision(source_revision) or not _hex64(execution_profile_id) or not _branch(branch):
   raise ValueError("invalid catalog identity or branch")
  if not _exact_int(prefix_tokens) or not _exact_int(capacity) or prefix_tokens<0 or capacity<=0 or prefix_tokens>capacity:
   raise ValueError("invalid catalog token counts")
  if base_id in by_id:raise ValueError("duplicate catalog base_id")
  by_id[base_id]=row
 return by_id

def resolve_base_proposal(text,catalog,*,required_revision,required_profile,reserve_tokens):
 if type(text) is not str or not text:raise ValueError("base proposal text required")
 if _utf8_length(text)>MAX_PROPOSAL_BYTES:raise ValueError("base proposal exceeds 65536 UTF-8 bytes")
 if not _revision(required_revision):raise ValueError("required_revision must be lowercase 40 or 64 hex")
 if not _hex64(required_profile):raise ValueError("required_profile must be lowercase 64 hex")
 if not _exact_int(reserve_tokens) or reserve_tokens<0:raise ValueError("reserve_tokens must be a nonnegative exact integer")
 try:proposal=json.loads(text,object_pairs_hook=_pairs,parse_constant=_constant)
 except (ValueError,RecursionError) as exc:raise ValueError("invalid base proposal JSON") from exc
 if type(proposal) is not dict or set(proposal)!=_PROPOSAL_KEYS:
  raise ValueError("base proposal fields are schema, base_id, reason only")
 if type(proposal["schema"]) is not int or proposal["schema"]!=1:raise ValueError("base proposal schema must be integer 1")
 base_id=proposal["base_id"]
 reason=proposal["reason"]
 if not _hex64(base_id):raise ValueError("base_id must be lowercase 64 hex")
 if type(reason) is not str or not reason.strip() or _utf8_length(reason)>MAX_REASON_BYTES:
  raise ValueError("reason must be nonblank text of at most 2048 UTF-8 bytes")
 by_id=_validate_catalog(catalog)
 chosen=by_id.get(base_id)
 if chosen is None:raise ValueError("unknown base_id")
 if chosen["source_revision"]!=required_revision or chosen["execution_profile_id"]!=required_profile:
  raise ValueError("chosen base does not match required revision or execution profile")
 if chosen["prefix_tokens"]+reserve_tokens>chosen["capacity"]:
  raise ValueError("reserve exceeds chosen base capacity")
 return dict(base=copy.deepcopy(chosen),reason=reason)
