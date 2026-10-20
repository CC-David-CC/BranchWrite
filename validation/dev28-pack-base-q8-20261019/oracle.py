import copy,random
from intervals import merge_intervals
rng=random.Random(47031)
for case in range(1000):
 rows=[sorted((rng.randrange(-12,13),rng.randrange(-12,13))) for _ in range(rng.randrange(13))]
 before=copy.deepcopy(rows)
 occupied=set()
 for a,b in rows:occupied.update(range(2*a,2*b+1))
 ordered=sorted(occupied);runs=[]
 for value in ordered:
  if not runs or value>runs[-1][1]+1:runs.append([value,value])
  else:runs[-1][1]=value
 assert all(a%2==0 and b%2==0 for a,b in runs)
 expected=[(a//2,b//2) for a,b in runs]
 source=iter(rows) if case%3==0 else rows
 actual=merge_intervals(source)
 assert type(actual) is list and all(type(pair) is tuple for pair in actual),(case,actual)
 assert actual==expected,(case,rows,expected,actual)
 assert rows==before,(case,'input mutated')
big=10**50
assert merge_intervals([(big,big+2),(big+1,big+3)])==[(big,big+3)]
try:merge_intervals([(0,1),(4,2)])
except ValueError:pass
else:raise AssertionError('reversed bounds accepted')
print('PASS: 1000 seeded interval-union cases, arbitrary-size integer and reversed-bound probes')
