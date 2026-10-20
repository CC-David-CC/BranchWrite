"""Pure validation of model-proposed repair steps, not an execution scheduler.

Role names select no permissions, templates, tools or model state here. The
existing interpreter owns any later admission; host verification owns completion.
A FIFO walk derives one reproducible dependency order in O(steps + edges).
"""
from collections import deque
import json,re

ROLES=frozenset(('diagnose','locate','edit','test','review'))
MAX_STEPS=32
MAX_PROPOSAL_BYTES=65536

def _pairs(rows):
 result={}
 for key,value in rows:
  if key in result:raise ValueError('duplicate task-breakdown key')
  result[key]=value
 return result

def _constant(value):raise ValueError('nonfinite task-breakdown value')

def parse_breakdown(text):
 """Return detached derived data; structural validity is not task acceptance."""
 if type(text) is not str or not text or len(text.encode('utf8'))>MAX_PROPOSAL_BYTES:
  raise ValueError('task breakdown requires at most 65536 UTF-8 bytes')
 try:proposal=json.loads(text,object_pairs_hook=_pairs,parse_constant=_constant)
 except (ValueError,RecursionError) as exc:raise ValueError('invalid task-breakdown JSON') from exc
 if (type(proposal) is not dict or set(proposal)!={'schema','steps'}
     or type(proposal['schema']) is not int or proposal['schema']!=1
     or type(proposal['steps']) is not list or not 1<=len(proposal['steps'])<=MAX_STEPS):
  raise ValueError('closed version-1 breakdown with 1..32 steps required')
 steps=[];by_id={}
 for row in proposal['steps']:
  if type(row) is not dict or set(row)!={'id','role','goal','depends_on'}:
   raise ValueError('step fields are id, role, goal, depends_on only')
  name=row['id'];role=row['role'];goal=row['goal'];deps=row['depends_on']
  if type(name) is not str or re.fullmatch('[A-Za-z][A-Za-z0-9_-]{0,63}',name) is None or name in by_id:
   raise ValueError('unique bounded step ID required')
  if type(role) is not str or role not in ROLES:raise ValueError('unsupported repair role')
  if type(goal) is not str or not goal.strip() or len(goal.encode('utf8'))>2048:
   raise ValueError('nonempty step goal of at most 2048 UTF-8 bytes required')
  if (type(deps) is not list or len(deps)>MAX_STEPS
      or any(type(d) is not str for d in deps) or len(set(deps))!=len(deps)):
   raise ValueError('distinct dependency IDs required')
  step=dict(id=name,role=role,goal=goal,depends_on=tuple(deps));by_id[name]=step;steps.append(step)
 outgoing={name:[] for name in by_id};indegree={name:0 for name in by_id}
 for step in steps:
  for dependency in step['depends_on']:
   if dependency not in by_id or dependency==step['id']:raise ValueError('unknown or self dependency')
   outgoing[dependency].append(step['id']);indegree[step['id']]+=1
 ready=deque(name for name in by_id if indegree[name]==0);order=[]
 while ready:
  name=ready.popleft();order.append(name)
  for dependent in outgoing[name]:
   indegree[dependent]-=1
   if indegree[dependent]==0:ready.append(dependent)
 if len(order)!=len(steps):raise ValueError('cyclic task breakdown')
 return dict(schema=1,steps=tuple(steps),order=tuple(order))
