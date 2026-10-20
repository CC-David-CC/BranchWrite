"""Build line-file teaching by executing real granted filesystem tools."""
import argparse,json,tempfile,hashlib
from pathlib import Path
from branchwrite.execution import Executor,Grant
from branchwrite.tool_registry import ToolRegistry

CASES=(
 dict(title="literal Unicode and LF",path="notes/session/report.txt",lines=["alpha '$USER'","next: \u03bb \u00e9 e\u0301"],line_ending="LF",final_newline=True,expected="alpha '$USER'\nnext: \u03bb \u00e9 e\u0301\n",repair=False),
 dict(title="CRLF without a final terminator",path="captures/output.txt",lines=["\u03b1","beta\t$USER"],line_ending="CRLF",final_newline=False,expected="\u03b1\r\nbeta\t$USER",repair=False),
 dict(title="read then repair the full file",path="drafts/result.txt",lines=["first row","second row: \u03a9"],line_ending="LF",final_newline=True,expected="first row\nsecond row: \u03a9\n",repair=True),
)

def build():
 lines=["# Text files with explicit lines","",
  "These are hypothetical examples on different files. Every action and feedback was executed through actual granted file tools. They are demonstrations, not the current task or extra permissions.",
  "Prefer create_text_file for a new ordinary text file. Each lines element holds one line without a CR or LF. line_ending selects LF or CRLF; final_newline is the explicit true/false choice. Preserve all Unicode code points, spaces, quotes, dollar text and tabs exactly.",
  "Use replace_text_file only when replacing the full file is appropriate. Read its current bytes first; the host binds the observation. For a small scoped change in a larger file, retain the existing replace tool and preserve every other byte.",
  "Do not add indentation to copied lines. Do not trim content or normalize accents. An empty file uses lines=[] with final_newline=false; one blank terminated line uses lines=[\"\"] with final_newline=true.",
  "For a blank line at the end,include an empty last element and set final_newline=true. A final empty element with final_newline=false is rejected.",
  "Read back the actual file before requesting finish. Compare every line and the final terminator. A proposed write or a plausible finish sentence is not successful verification.",
  "Examples may contain tools or paths absent from your current grant. The live schema and host remain authoritative.",""]
 for index,case in enumerate(CASES,1):
  with tempfile.TemporaryDirectory(prefix="bw-line-example-") as tmp:
   root=Path(tmp);source=root/"source";source.mkdir();(source/"keep.txt").write_bytes(b"keep\n")
   executor=Executor.create(source,root/"world");path=case["path"]
   registry=ToolRegistry(executor,Grant((path,) if case["repair"] else (),False,create_paths=(path,),read_paths=(path,)))
   spec={k:v for k,v in case.items() if k!="expected"};spec["utf8_hex"]=case["expected"].encode().hex()
   lines.extend(["## Line file example "+str(index)+": "+case["title"],"TASK: "+json.dumps(spec,ensure_ascii=True),""])
   good=dict(path=path,lines=case["lines"],line_ending=case["line_ending"],final_newline=case["final_newline"])
   initial=dict(good)
   if case["repair"]:initial["lines"]=[case["lines"][0]," "+case["lines"][1]];initial["final_newline"]=False
   actions=[dict(tool="create_text_file",arguments=initial),dict(tool="read_file",arguments=dict(path=path))]
   if case["repair"]:actions.extend([dict(tool="replace_text_file",arguments=good),dict(tool="read_file",arguments=dict(path=path))])
   actions.append(dict(tool="finish",arguments=dict(answer="The actual readback matches the requested text and line endings.")))
   observations=();latest=None
   for number,action in enumerate(actions):
    if action["tool"]=="finish":assert latest==case["expected"].encode()
    result=registry.execute(registry.freeze(json.dumps(action),observations=observations),"line-example-"+str(index)+"-"+str(number))
    if result.observation is not None:observations+=(result.observation,)
    feedback=dict(tool=result.tool,disposition=result.disposition,exit_code=result.exit_code,stdout=result.stdout.decode(),stderr=result.stderr.decode(),
     observation=None if result.observation is None else dict(world=result.observation.world,path=result.observation.path,source_sha256=result.observation.sha256))
    lines.extend(["ACTION: "+json.dumps(action,ensure_ascii=True),"FEEDBACK: "+json.dumps(feedback,ensure_ascii=True),""])
    if action["tool"]=="read_file":
     latest=result.stdout
     lines.append("Readback comparison: "+("exactly matches, including the final-newline choice." if latest==case["expected"].encode() else "wrong indentation and missing final terminator. Use the granted full-file replacement with the correct lines and final_newline=true; do not claim finish."))
   assert (executor.workspace/path).read_bytes()==case["expected"].encode()
   assert (executor.workspace/"keep.txt").read_bytes()==b"keep\n"
 return "\n".join(lines)+"\n"

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--output",type=Path,required=True);args=parser.parse_args()
 body=build().encode();args.output.write_bytes(body)
 print(json.dumps(dict(status="ACTUAL_LINE_FILE_EXAMPLES_BUILT",examples=len(CASES),bytes=len(body),sha256=hashlib.sha256(body).hexdigest())))
if __name__=="__main__":main()
