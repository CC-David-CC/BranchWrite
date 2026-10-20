from pathlib import Path
import json,sys,time,statistics
from branchwrite.execution import Executor,Grant
from branchwrite.records import RuntimeLog
from branchwrite.kernel import FrameKernel,ResultContract
from branchwrite.tool_registry import ToolRegistry
from branchwrite.tool_dispatch import admit_tool,dispatch_tool
import branchwrite
d=Path(sys.argv[1]);d.mkdir();src=d/'source';src.mkdir();(src/'data.txt').write_bytes(b'a'*1024)
executor=Executor.create(src,d/'world');registry=ToolRegistry(executor,Grant((),False,read_paths=('data.txt',)))
samples=[];events=[]
with RuntimeLog(d/'ledger') as log:
 k=FrameKernel(log);k.create_root('root','root-attempt',log.put_artifact(b'FLOW bench\nEND\n'),log.put_artifact(b'read'),ResultContract('AgentResult','record'))
 for i in range(30):
  admit_tool(k,registry,'root',expected_epoch=i,child_id='tool-'+str(i),attempt_id='attempt-'+str(i),slot='out',next_pc=i+1,proposal=json.dumps(dict(tool='read_file',arguments=dict(path='data.txt'))))
  before=log.event_count;t=time.perf_counter_ns();v=dispatch_tool(k,registry,'tool-'+str(i));elapsed=time.perf_counter_ns()-t
  assert v['disposition']=='read'
  if i>=5:samples.append(elapsed);events.append(log.event_count-before)
  k.resume('root',i+1)
result=dict(module_path=branchwrite.__file__,measured_calls=len(samples),warmup_calls=5,median_dispatch_ms=statistics.median(samples)/1e6,samples_ns=samples,dispatch_events=sorted(set(events)),scope='1KiB actual read and durable dispatch publication, no inference; initialization/admission/parent resume excluded.')
(d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
