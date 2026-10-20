# Selective thinking escalation

The short greedy image question previously failed at128 reasoning tokens,
returning NOT_VISIBLE despite describing the square as upper-left. The new run
keeps the same image/question, native/model, greedy policy and thinking renderer.
Only the diagnostic runner adds selective budgets and stopping at natural closure.

| Budget | Actual thought tokens | Closure | Final | Quality |
|---|---:|---|---|---|
|128, earlier run|128|budget|NOT_VISIBLE|FAIL retained|
|256|256|budget|LEFT|PASS|
|512|358|natural|LEFT|PASS|

Only the failing short/greedy arm ran. Passing expanded/sampled cases did not
repeat. Escalation stopped at natural closure, not merely the forced256 success;
a naturally wrong final would have stopped it too.1024+ did not run. Each budget
forks the prepared root into its own immutable grammar scope, then pauses after
four tokens and resumes. Root checkpoint bytes and partial controllers remain
unchanged, and native forward work matches generated IDs at each request.

Real llm-60 GPU=[0], Q4/FP16 KV, authenticated CLI/HTTP/COW.13 focused/74 affected
CPU checks and G0 51 pass; no green failures/errors/skips. RED import failure and
an initial G0 report-write failure are retained. The latter was a launcher error
on frozen source; --no-write fixed reporting. Python/native exited0 and are
absent. Chat OFF. No full-vector oracle, peak-memory/performance qualification,
Q8, restart/fault campaign or general answer-quality guarantee.

COW implementation/evidence commit6baf00225d5d82704f2a04d56f025cd89fdc87d8
is verified on private box-git task and feat/cow-vision-inputs refs. Exact profile
31a2a83829379944a2714937cd644785480157d11f8148adf43dc3dbb39aa37e.
See COW experimental/branching_context/evidence/THINKING-NATURAL-END-Q4-2026-10-17.json.
Raw private archive:
box-git:/srv/data/git/private_context_cow.evidence/20261017-cow-thinking-natural-v1/evidence.tar.gz
5083571 bytes,136 members,SHA256
781a93a2ebbac88d0cb62c7454281c213b1c267247b9ae990567eb823a80df93.
Every archived member and receiver bytes/hash verified; derived KV excluded with
byte/hash inventory and retained on llm-60.

Failure candidates, successful mitigations and generator briefs are saved under
fleet/branchwrite-lora-examples/candidates/. No automatic training, approval or
export of protected diagnostic answers. H04/H05 minimal edit/image-driven repair
are next; basic path first, selective thinking escalation after failure.
