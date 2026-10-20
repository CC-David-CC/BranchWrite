"""Generate reusable literal-file demonstrations using actual registered tools.
No inference, protected fixtures, shell grants or current task answers.
"""
import argparse,json,tempfile
from hashlib import sha256
from pathlib import Path
from branchwrite.execution import Executor,Grant
from branchwrite.tool_registry import ToolRegistry

CASES=(
 ("nested literal text","notes/session/report.txt","say 'hello' $USER\nnext: \u03bb \u00e9 e\u0301\n",False),
 ("CRLF and no final newline","captures/line endings.txt","\u03b1\r\nbeta\t$USER",False),
 ("repair unwanted indentation","drafts/receipt.txt","first row\nsecond row: \u03a9\n",True),
)

def build():
    lines=["# Literal file operations","",
      "These are hypothetical tasks on different files, not the current task. Actions and feedback were executed through the real registered file tools.",
      "Do not add indentation when copying lines from a code block. Preserve Unicode code points, spaces, quotes, dollar expressions and line endings exactly. JSON escapes encode characters, not literal backslash text.",
      "A create grant permits the exact leaf and its necessary private parents. It never permits overwriting an existing file. Read back the actual bytes before requesting finish. A create receipt alone is not readback.",
      "If readback is wrong, repair only with an explicit edit grant and the latest observation. Without an edit grant, report the limitation; do not claim success or invent tools.",
      "Example paths, byte counts, hex strings and observation identities are not permissions or answers to copy into another task. Preserve existing neighbors.",""]
    for index,(title,path,expected,repair) in enumerate(CASES,1):
        with tempfile.TemporaryDirectory(prefix="bw-literal-example-") as tmp:
            root=Path(tmp);source=root/"source";source.mkdir();(source/"neighbor.txt").write_bytes(b"keep\n")
            executor=Executor.create(source,root/"world")
            registry=ToolRegistry(executor,Grant((path,) if repair else (),False,create_paths=(path,),read_paths=(path,)))
            body=expected.encode()
            spec=dict(title=title,path=path,utf8_hex=body.hex(),utf8_bytes=len(body),text=expected,repair=repair)
            lines.extend(["## Literal file example "+str(index)+": "+title,"TASK: "+json.dumps(spec,ensure_ascii=True),""])
            content=expected.replace("\nsecond row","\n second row") if repair else expected
            actions=[dict(tool="create_file",arguments=dict(path=path,content=content)),dict(tool="read_file",arguments=dict(path=path))]
            if repair:
                actions.extend([dict(tool="replace",arguments=dict(path=path,before="\n second row",after="\nsecond row")),dict(tool="read_file",arguments=dict(path=path))])
            actions.append(dict(tool="finish",arguments=dict(answer="Created the requested file and read back its exact bytes.")))
            latest=None;observations=()
            for number,action in enumerate(actions):
                if action["tool"]=="finish":
                    assert latest==body and (executor.workspace/path).read_bytes()==body
                outcome=registry.execute(registry.freeze(json.dumps(action),observations=observations),"example-"+str(index)+"-"+str(number))
                if outcome.observation is not None:observations+=(outcome.observation,)
                feedback=dict(tool=outcome.tool,disposition=outcome.disposition,exit_code=outcome.exit_code,
                    stdout=outcome.stdout.decode(),stderr=outcome.stderr.decode(),
                    observation=None if outcome.observation is None else dict(world=outcome.observation.world,path=outcome.observation.path,source_sha256=outcome.observation.sha256))
                lines.extend(["ACTION: "+json.dumps(action,ensure_ascii=True),"FEEDBACK: "+json.dumps(feedback,ensure_ascii=True),""])
                if action["tool"]=="read_file":
                    latest=outcome.stdout
                    lines.append("Byte comparison: "+("matches the requested bytes." if latest==body else "does NOT match: the second line has an unwanted leading space. Use the permitted exact replacement; do not request finish."))
            assert (executor.workspace/"neighbor.txt").read_bytes()==b"keep\n"
    return "\n".join(lines)+"\n"

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--output",type=Path,required=True);args=parser.parse_args()
    body=build().encode();args.output.write_bytes(body)
    print(json.dumps(dict(status="ACTUAL_FILE_TOOL_EXAMPLES_BUILT",examples=len(CASES),bytes=len(body),sha256=sha256(body).hexdigest())))
if __name__=="__main__":main()
