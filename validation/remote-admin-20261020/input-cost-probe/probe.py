import cProfile,pstats,io,time,json
from pathlib import Path
from context_time_travel.input_spans import InputHistory
from context_time_travel.vision_execution import input_binding
r=Path(__file__).parent;rows=[]
def exercise(n,steps):
 h=InputHistory([dict(kind='text',tokens=[(i*7919+17)%200000 for i in range(n)])])
 for i in range(steps):
  before=len(h);current=h+(41+i,)
  assert current.prefix(before)==h
  assert current.segment(before).native_tokens==(41+i,)
  input_binding(current);input_binding(current)
  h=current
for n in [1024,8192,32768]:
 start=time.perf_counter();exercise(n,20);rows.append(dict(prefix=n,steps=20,seconds=time.perf_counter()-start))
p=cProfile.Profile();p.enable();exercise(32768,20);p.disable();stream=io.StringIO();pstats.Stats(p,stream=stream).sort_stats('cumulative').print_stats(25)
(r/'profile.txt').write_text(stream.getvalue());(r/'result.json').write_text(json.dumps(dict(scope='CPU-only synthetic execution of actual input-view/schedule functions; not an end-to-end GPU profile',source='/home/dflanag3/src/context-cow-client-setup-20261020',rows=rows),indent=2)+'\n')
print(json.dumps(rows));print(stream.getvalue()[:5000])
