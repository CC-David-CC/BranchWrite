# Smaller repair steps with shared computational history

A repair can be divided into diagnosis, locating code, editing, testing and
review. Related tasks can reuse the same prepared repository context, while
each worktree keeps its own files and continuation. A focused step may instead
start from another prepared instruction/example prefix and receive the exact
current task and evidence. Starting another model context never undoes effects.

## Delivered source dev20 boundary

The existing interpreter accepts:

    EXPAND propose from=current task=goal profile=planner -> proposal
    TRANSFORM validate input=proposal contract=task-breakdown -> breakdown

The planner is an existing host-admitted generation profile. Its JSON proposal
contains schema1 and1..32steps. Each step has exactly id,role,goal,depends_on.
Roles are diagnose,locate,edit,test,review. IDs are unique and bounded. References
may point forward;unknown dependencies,duplicates,self-dependencies and cycles
fail. A deterministic FIFO walk derives the order in linear nodes+edges work.
No tool,grant,template path,budget or verified flag is admitted from the model.
UTF-8 proposal and goal byte limits are explicit,not silently truncated.

The transform returns typed TaskBreakdown data with valid,plan,reason and source
provenance. An invalid proposal is a retained rejection value. It cannot execute
anything or become successful host verification. Both valid and invalid results
reference the original completed model frame,its frozen inputs,source snapshot
and output hash. They are ordinary immutable derived artifacts in RuntimeLog,
not another history store or scheduler. Closed workflows reopen without another
model request. The role is descriptive;it selects no permissions or prefill yet.

Source validation:42 combined CPU/HTTP/interpreter/recovery methods passed,
including9validator and2flow tests. Model responses are scripted CPU fixtures;
no autonomous planning-quality or GPU qualification is claimed. The first flow
fixture used the wrong initial context boundary;the server rejected it. That
failure remains in evidence and the fixture now uses the closed-root operation.

## Remaining integration and acceptance

1. Build related worktree tasks from one immutable context root. Keep grants,
   ledgers,workspaces,observations and verification separate;exclude Git's shared
   administrative paths from candidate capabilities. Prove edits/test receipts
   cannot cross worlds even when histories share an ancestor.
2. Bind host-selected role-to-prefix references and explicit current evidence to
   each ready child in the existing FrameKernel. Store immutable references,not
   a second live task queue. One GPU executes serially;later completions may
   arrive out of order and must bind the original child/slot/epoch.
3. Validate each step against its host completion contract. A model explanation
   or test result from another worktree/revision is not sufficient. Dependent
   steps wait for committed evidence;uncertain effects block continuation.
4. On a failed check,retain the attempt and its evidence and admit revised work
   from an appropriate saved context. Do not silently undo edits or regenerate
   acknowledged results. Selecting a fresh prefill computes the new input under
   its actual profile;it is not a numerical continuation of removed text.
5. Test restart,cancellation,changed files,late results,failed-plan recovery and
   one-live-Q8 coding decomposition before exposing this as normal autonomous
   scheduling. Preserve the original G/VC/cross-arrangement limitations.

The new interpreter source identity differs from older packages. Do not replace
an active or pending run's pinned interpreter. Installed dev19 remains unchanged;
source dev20 is not an automatic migration or a delivered multi-worktree agent.

## Related-worktree boundary checked

Real Git worktrees from one commit were admitted as separate owned execution
worlds. Git's shared administrative paths were excluded. A's read observation
and frozen edit plan were rejected by B even when file content hashes matched.
An edit and passing test in A left B unchanged and its own test failing;both
original worktree inputs remained unchanged. A local HTTP/CPU COW test forked
two continuations from the exact same saved prefix,proved their tips diverged
without moving their parent or each other,and retained the foreign-world
observation refusal.11combined checks pass,including these four new cases.

No implementation fix was needed for this boundary. It validates existing
isolation,not physical GPU sharing or autonomous multi-worktree scheduling. See
validation/RELATED-WORKTREES-2026-10-19/. Role-specific prefill binding and actual
ready-child admission are still the next implementation work.
