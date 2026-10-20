"""Seeded, model-free terminal components using the actual tool boundary.

Each domain can be run before an autonomous task, independently of prompts.
These are new synthetic fixtures, not protected catalogue answers. Expectations
are authored from byte literals and Bash semantics before execution. Observed
output never becomes its own oracle. A component PASS says the tool boundary
worked; it does not certify that a model can interpret or report that result.
"""
from pathlib import Path
import argparse,hashlib,json,os,shlex,sys,time,traceback
from .execution import Executor,Grant
from .terminal import ShellConfig
from .tool_registry import ToolRegistry
from .records import RuntimeLog,Artifact
from .kernel import FrameKernel
from .interpreter import Interpreter,Value

DOMAINS=("streams","warning-success","pipeline","binary","literal-ufffd",
         "empty","missing-file","quoting","timeout","recovery","newlines")
SPLITS=("demo","heldout")

def _sha(raw):
 return hashlib.sha256(raw).hexdigest()

def _step(command,stdout=b"",stderr=b"",exit_code=0,**constraints):
 return dict(command=command,expected=dict(stdout_hex=stdout.hex(),
  stderr_hex=None if stderr is None else stderr.hex(),exit_code=exit_code,
  **({"disposition":"exited"} | constraints)))

def _py(code):
 return "/usr/bin/python3 -I -B -c "+shlex.quote(code)

def build_case(domain,*,seed=731,split="demo"):
 """Construct a reproducible fixture without executing or reading model data."""
 if domain not in DOMAINS or split not in SPLITS or type(seed) is not int or not 0<=seed<2**63:
  raise ValueError("known component, demo/heldout split and unsigned 63-bit seed required")
 token=hashlib.sha256((str(seed)+":"+split+":"+domain).encode()).hexdigest()[:14]
 code=17+int(token[:2],16)%90
 marker=("case-"+token+"\n").encode()
 files={}
 if domain=="streams":
  out=b"COMPLETED "+marker;err=b"failure-detail "+marker
  steps=[_step(_py("import os;os.write(1,"+repr(out)+");os.write(2,"+repr(err)+");raise SystemExit("+str(code)+")"),out,err,code)]
 elif domain=="warning-success":
  out=b"result "+marker;err=b"warning-only "+marker
  steps=[_step(_py("import os;os.write(1,"+repr(out)+");os.write(2,"+repr(err)+")"),out,err)]
 elif domain=="pipeline":
  pipeline="printf '%s\\n' "+shlex.quote("present-"+token)+" | grep -F "+shlex.quote("absent-"+token)+" | cat"
  steps=[_step(pipeline),_step("set -o pipefail; "+pipeline,exit_code=1)]
 elif domain=="binary":
  out=b"\xff\x00"+marker+b"\x80";err=b"\xfe"+marker+b"\x81"
  steps=[_step(_py("import os;os.write(1,"+repr(out)+");os.write(2,"+repr(err)+");raise SystemExit("+str(code)+")"),out,err,code)]
 elif domain=="literal-ufffd":
  out=("\ufffd is intentional "+token+"\n").encode()
  steps=[_step(_py("import os;os.write(1,"+repr(out)+")"),out)]
 elif domain=="empty":
  steps=[_step("true"),_step("false",exit_code=1)]
 elif domain=="missing-file":
  name="empty-"+token+".txt";files[name]=""
  absent="absent-"+token+".txt"
  steps=[_step("test -e "+shlex.quote(absent),exit_code=1),
         _step("test -e "+shlex.quote(name)),_step("cat -- "+shlex.quote(name))]
 elif domain=="quoting":
  name="notes "+token+" '$HOME' \u0394.txt"
  out=("literal $HOME; 'single' \"double\" \u0394 "+token+"\n").encode()
  files[name]=out.decode()
  steps=[_step("cat -- "+shlex.quote(name),out)]
 elif domain=="newlines":
  literal=("line-"+token).encode()
  values=[literal+b"\n",literal,literal+b"\r\n",literal+b"\\n"]
  steps=[_step(_py("import os;os.write(1,"+repr(raw)+")"),raw) for raw in values]
 elif domain=="timeout":
  steps=[_step(_py("import os,time;os.write(1,"+repr(marker)+");time.sleep(60)"),marker,
   exit_code=None,disposition="timeout",negative_status=True)]
 else:
  missing="bw_missing_"+token
  steps=[_step(missing,stderr=None,exit_code=127,stderr_contains="command not found"),
         _step("printf '%s\\n' "+shlex.quote("recovered-"+token),("recovered-"+token+"\n").encode())]
 # Held-out cases change operation structure and content, not just random labels.
 # They remain independent synthetic tool fixtures, not model-performance claims.
 if split=="heldout":
  if domain=="streams":
   out=b"COMPLETED "+marker;err=b"failure-detail "+marker
   steps=[_step("printf '%s' "+shlex.quote(out.decode())+"; printf '%s' "+shlex.quote(err.decode())+" >&2; exit "+str(code),out,err,code)]
  elif domain=="warning-success":
   out=b"result "+marker;err=b"warning-only "+marker
   steps=[_step("printf '%s' "+shlex.quote(err.decode())+" >&2; printf '%s' "+shlex.quote(out.decode()),out,err)]
  elif domain=="pipeline":
   pipeline="printf '%s\\n' "+shlex.quote("present-"+token)+" | grep -F "+shlex.quote("absent-"+token)+" | wc -l"
   steps=[_step(pipeline,b"0\n"),_step("set -o pipefail; "+pipeline,b"0\n",exit_code=1)]
  elif domain=="binary":
   out=b"header:"+marker+b"\xf0\x28\x8c\x28\x00";err=b"error:\xed\xa0\x80"+marker
   steps=[_step(_py("import sys;sys.stderr.buffer.write("+repr(err)+");sys.stdout.buffer.write("+repr(out)+");sys.exit("+str(code)+")"),out,err,code)]
  elif domain=="literal-ufffd":
   out=("literal \ufffd twice \ufffd "+token+"\n").encode()
   steps=[_step("printf '%s' "+shlex.quote(out.decode()),out)]
  elif domain=="empty":
   steps=[_step(_py("raise SystemExit(0)")),_step(_py("raise SystemExit(1)"),exit_code=1)]
  elif domain=="missing-file":
   name=next(iter(files));absent="absent-"+token+".txt"
   steps=[_step("[ -f "+shlex.quote(name)+" ]"),
          _step("[ -s "+shlex.quote(name)+" ]",exit_code=1),
          _step("[ -f "+shlex.quote(absent)+" ]",exit_code=1),
          _step("cat -- "+shlex.quote(name))]
  elif domain=="quoting":
   name="two spaces  "+token+" $HOME ' \" \u00e9 e\u0301 \U0001f42e.txt"
   text="literal $HOME | $"+chr(123)+"USER} | $(id) | 'single' | \"double\" | \u00e9 e\u0301 \u0394 \U0001f42e"
   files={name:text}
   steps=[_step("cat -- "+shlex.quote(name),text.encode()),
          _step("printf '%s\\n' "+shlex.quote(text),(text+"\n").encode())]
  elif domain=="newlines":
   text="\u00e9 e\u0301 $HOME "+token
   values=[text+"\n",text,text+"\r\n",text+"\\n",text+"\n\n"]
   steps=[_step("printf '%s' "+shlex.quote(raw),raw.encode()) for raw in values]
  elif domain=="timeout":
   steps=[_step("printf '%s' "+shlex.quote(marker.decode())+"; sleep 60",marker,
    exit_code=None,disposition="timeout",negative_status=True)]
  elif domain=="recovery":
   steps=[_step("command -- bw_missing_"+token,stderr=None,exit_code=127,stderr_contains="not found"),
          _step(_py("print("+repr("recovered-"+token)+")"),("recovered-"+token+"\n").encode())]
 return dict(schema=1,id="TC"+str(DOMAINS.index(domain)+1).zfill(3)+"-"+split+"-"+token,
  domain=domain,seed=seed,split=split,files=files,steps=steps,
  timeout_seconds=0.5 if domain=="timeout" else 3.0,
  expectation_origin="synthetic byte literals and Bash semantics; computed before execution")

def _stream(raw):
 return dict(bytes=len(raw),sha256=_sha(raw),hex=raw.hex())

def _valid_utf8(raw):
 try:raw.decode("utf8")
 except UnicodeDecodeError:return False
 return True

def _compare(expected,outcome,view,out,err,command):
 checks=dict(disposition=outcome["disposition"]==expected["disposition"],
  command=view.get("command")==command,
  worker_exited=outcome["details"]["isolation"]["worker_exited"] is True,
  namespace_retired=outcome["details"]["isolation"]["namespace_members_after"]==[])
 if expected.get("negative_status"):
  checks["exit_code"]=type(outcome["exit_code"]) is int and outcome["exit_code"]<0
 else:checks["exit_code"]=outcome["exit_code"]==expected["exit_code"]
 for field,raw in (("stdout",out),("stderr",err)):
  if expected[field+"_hex"] is not None:checks[field+"_bytes"]=raw.hex()==expected[field+"_hex"]
  if field+"_contains" in expected:checks[field+"_contains"]=expected[field+"_contains"].encode() in raw
  checks[field+"_artifact"]=view[field+"_artifact"]==dict(bytes=len(raw),sha256=_sha(raw))
  checks[field+"_untruncated"]=view[field+"_truncated"] is False
  display=view[field+"_display"]
  checks[field+"_display"]=(display==dict(encoding="utf-8",errors="replace",
    lossy=not _valid_utf8(raw),source_bytes=len(raw)))
  checks[field+"_text"]=view[field]==raw.decode("utf8","replace")
 return checks

def run_case(case,output_dir):
 """Run one fresh real sandbox case. Never reuse an existing result directory."""
 # Rebuild author-defined expectations, rejecting caller-supplied expected results.
 expected_case=build_case(case["domain"],seed=case["seed"],split=case["split"])
 if expected_case!=case:raise ValueError("case differs from deterministic definition")
 root=Path(output_dir);root.mkdir(mode=0o700)
 source=root/"source";source.mkdir(mode=0o700)
 for name,text in case["files"].items():(source/name).write_bytes(text.encode())
 (root/"fixture.json").write_text(json.dumps(case,indent=2,ensure_ascii=True)+"\n")
 started=time.monotonic()
 record=dict(schema=1,id=case["id"],domain=case["domain"],seed=case["seed"],split=case["split"],
  model_inference=False,fixture_sha256=_sha(json.dumps(case,sort_keys=True).encode()),
  hostname=os.uname().nodename,observations=[],status="ERROR")
 try:
  executor=Executor.create(source,root/"world",shell=ShellConfig(timeout=case["timeout_seconds"],
   expected_hostname=os.uname().nodename))
  registry=ToolRegistry(executor,Grant((),False,read_paths=tuple(case["files"]),allow_shell=True))
  lines=["FLOW component"];bindings={}
  for index,step in enumerate(case["steps"]):
   name="proposal"+str(index)
   bindings[name]=Value("ToolProposal",json.dumps(dict(tool="run_shell",arguments=dict(command=step["command"]))))
   lines.extend([f"PLAN p{index} from={name} against=world -> plan{index}",
    f"ACT a{index} plan=plan{index} -> outcome{index}",
    f"TRANSFORM v{index} contract=tool-feedback input=outcome{index} -> view{index}"])
  lines.append("END")
  with RuntimeLog(root/"ledger") as log:
   runtime=Interpreter(FrameKernel(log),registry);runtime.start("\n".join(lines)+"\n",bindings)
   result=runtime.run()
   if result.status!="complete":raise RuntimeError("component workflow did not complete: "+str(result.status))
   for index,step in enumerate(case["steps"]):
    outcome=result.value["bindings"]["outcome"+str(index)][1]
    view=json.loads(result.value["bindings"]["view"+str(index)][1])
    out=log.read_artifact(Artifact(*outcome["stdout"]));err=log.read_artifact(Artifact(*outcome["stderr"]))
    checks=_compare(step["expected"],outcome,view,out,err,step["command"])
    record["observations"].append(dict(index=index,command=step["command"],expected=step["expected"],
     actual=dict(disposition=outcome["disposition"],exit_code=outcome["exit_code"],
      stdout=_stream(out),stderr=_stream(err)),
     feedback=view,operation_id=outcome["operation_id"],plan_sha256=outcome["plan_sha256"],
     isolation=outcome["details"]["isolation"],checks=checks,
     status="PASS" if all(checks.values()) else "FAIL"))
  record["status"]="PASS" if all(row["status"]=="PASS" for row in record["observations"]) else "FAIL"
 except Exception:
  record["error"]=traceback.format_exc()
 record["elapsed_seconds"]=time.monotonic()-started
 (root/"result.json").write_text(json.dumps(record,indent=2,ensure_ascii=True)+"\n")
 return record

def main(argv=None):
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument("--domain",choices=DOMAINS,action="append",help="Repeat to select independent components; default all")
 parser.add_argument("--split",choices=SPLITS,default="heldout")
 parser.add_argument("--seed",type=int,default=731)
 parser.add_argument("--variants",type=int,default=1)
 parser.add_argument("--output-dir",type=Path,required=True)
 args=parser.parse_args(argv)
 if not 1<=args.variants<=100:parser.error("--variants must be 1..100")
 if not 0<=args.seed<2**63 or args.seed+args.variants>2**63:parser.error("seed range exceeds unsigned 63-bit range")
 args.output_dir.mkdir(mode=0o700)
 records=[]
 for seed in range(args.seed,args.seed+args.variants):
  for domain in args.domain or DOMAINS:
   case=build_case(domain,seed=seed,split=args.split)
   result=run_case(case,args.output_dir/case["id"])
   records.append(result)
   print(json.dumps(dict(id=result["id"],status=result["status"],elapsed_seconds=result["elapsed_seconds"])),flush=True)
   report=dict(schema=1,model_inference=False,scope="terminal transport components; no autonomous model qualification",
    cases=len(records),passed=sum(r["status"]=="PASS" for r in records),
    failed=sum(r["status"]=="FAIL" for r in records),errors=sum(r["status"]=="ERROR" for r in records),
    skipped=0,records=records)
   (args.output_dir/"report.json").write_text(json.dumps(report,indent=2)+"\n")
 return 0 if all(r["status"]=="PASS" for r in records) else 1

if __name__=="__main__":sys.exit(main())
