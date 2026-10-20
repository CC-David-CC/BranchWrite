"""Independent checks; run against an exported terminal candidate, not live state."""
import importlib.util,json,sys,copy
from pathlib import Path
path=Path(sys.argv[1]).resolve(strict=True)
spec=importlib.util.spec_from_file_location("candidate_base_choice",path)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
f=m.resolve_base_proposal
revision="a"*40;profile="b"*64
rows=[dict(base_id=c*64,branch="base-"+c,snapshot="e"*64,source_revision=revision,execution_profile_id=profile,prefix_tokens=n,capacity=262144) for c,n in [("1",147997),("2",29334),("3",44676)]]
assert len(('\u00e9'*1025).encode('utf8'))==2050
checks=[0]
def reject(text,catalog=rows,**overrides):
 kw=dict(required_revision=revision,required_profile=profile,reserve_tokens=8192);kw.update(overrides)
 try:f(text,catalog,**kw)
 except ValueError:checks[0]+=1;return
 raise AssertionError("invalid proposal accepted")
for row in rows:
 before=copy.deepcopy(rows);proposal=json.dumps(dict(schema=1,base_id=row["base_id"],reason="Compare this recorded base."))
 result=f(proposal,rows,required_revision=revision,required_profile=profile,reserve_tokens=8192)
 assert result==dict(base=row,reason="Compare this recorded base.") and rows==before
 result["base"]["branch"]="changed";assert rows==before;checks[0]+=1
 reject(proposal,reserve_tokens=262144-row["prefix_tokens"]+1)
for raw in ['NaN','[]','null','{"schema":1,"schema":1,"base_id":"'+"1"*64+'","reason":"x"}']:
 reject(raw)
base=dict(schema=1,base_id="1"*64,reason="x")
for key,value in [("schema",True),("schema",1.0),("reason"," "),("reason","\u00e9"*1025),("base_id","A"*64)]:
 value_record=dict(base);value_record[key]=value;reject(json.dumps(value_record))
for key,value in [("prefix_tokens",True),("capacity",1.0),("snapshot","../secret"),("branch"," ")]:
 catalog=copy.deepcopy(rows);catalog[2][key]=value;reject(json.dumps(base),catalog)
reject(json.dumps(base),rows+[copy.deepcopy(rows[0])])
reject(json.dumps(base),required_revision="f"*40)
reject(json.dumps(base),required_profile="f"*64)
print(json.dumps(dict(status="PASS",checks=checks[0],scope="independent host-validator checks; not inference qualification")))
