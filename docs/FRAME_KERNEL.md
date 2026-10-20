# Production frame and return controller

BranchWrite can now save who is waiting for which result. If two pieces of work
finish in the opposite order, each result still goes to its own slot. If the
program restarts after a tool finishes, that saved result remains available.
The general model-driven decision loop and its CLI are still being built.

FrameKernel in branchwrite/kernel.py is the one production controller for this
state. It uses RuntimeLog; it imports no protected reference implementation and
creates no alternative model transcript, scheduler daemon or storage format.
This supports R05 but does not qualify every registered R05 case or an autonomous
workload. COW continues to own token history, positions, native grammar/sampler
state, checkpoints and branch references. Those are opaque external bindings to
be supplied through the existing COW adapter, not reimplemented by the kernel.

## What the kernel owns

A frame freezes its identity/attempt, parent/epoch/slot, operation/definition,
exact input artifact, named result contract, program counter and state. Definition
and input bytes must already exist in the durable artifact store. The current
ResultContract checks an exact top-level primitive type and canonical nested
values; it does not yet validate arbitrary nested product schemas. Bool/int and
text/bytes remain different. Contract identities bind name and shape.

The root is a FLOW invocation. Spawn admits a bounded tuple of child calls and
all named parent waits in one durable event. Calls have unique child and slot
identities; each child has independent future state. The parent is Waiting until
all slots are filled and resume is durably recorded. The host selects the next
program position; a model cannot supply a trusted return address through this
internal API. Program parsing and admission are a forthcoming boundary.

The lifecycle is Ready -> Waiting for a dispatched operation -> Settling if its
result is known but resources remain unresolved -> Closed after settlement.
A returned child is retained historically. The parent separately becomes Ready
at its pinned continuation after every required slot is filled. A partial native
model turn is not thereby a completed child result; the COW adapter must enforce
its consumed/durable/complete-output contract before delivering a value.

## Durable transitions

Every event has schema1 and a known kind with an exact field set. RuntimeLog's
artifact roots must match the event's references. Reopen verifies storage hashes,
then revalidates every semantic transition. A checksummed impossible frame event
is still rejected. In-memory state is a detached derived projection.

| Event | Durable transition |
|---|---|
| root | Admit one root and its immutable definition/input/contract |
| spawn | Admit children and parent waits together, binding source epoch and next PC |
| dispatched | Retain original operation ID and exact request artifact before external send |
| returned | Retain typed result/provenance artifact; deliver only after resource settlement |
| settled | Retain a host-observed settlement receipt, close child, fill its original slot |
| resumed | Record parent resumption once before subsequent dispatch |
| finished | Return a settled FLOW value, close it and fill its parent slot |

Dispatch returns True only when a new intent was committed. An identical retry
returns False: the adapter must reconcile the original operation, never resend a
nonrepeatable effect merely because it sees that result. A changed operation or
request cannot replace a pending call. Operation IDs cannot belong to two frames.
A False result after an already completed call likewise does not authorize work.
The kernel cannot repair an adapter that ignores this rule; full adapter recovery
and actual client/effect exactly-once behavior remain separate qualification.

Results bind the original operation, frozen result contract and provenance. An
identical return is idempotent. A conflicting return cannot overwrite a slot.
Unsettled results remain Settling and cannot resume the parent; closing them
requires a separately retained host settlement receipt. The internal settled flag
is a trusted adapter observation, never an accepted model authorization field.
This layer does not verify OS containment or manufacture a process-exit fact.

An old group's duplicate result cannot fill a new group's same-named slot.
Independent sibling returns may arrive in either order. No launch/completion order
selects a result destination. Resume is idempotent for its exact parent epoch.
A stale second controller facade cannot mutate the same log. The O(1) log cursor
checks single-controller ownership, not model-plan dependency freshness; relevant
state/permission/resource validation at actual dispatch still needs R08/R09 wiring.

## Failed writes and restart

Result artifacts are published before return events. If an artifact flush fails
before an event is written, no call is admitted. If event durability is uncertain,
the log and controller stop serving a current projection until reopen/reconcile.
They never treat an old cached projection as proof of noncommitment.

Tests independently reopen after result publication but before parent resume,
and after a pending dispatch. One cooperative real subprocess increments a file,
its result is retained, and the producer exits47 without cleanup. Reopen retains
the exact bytes, refuses a second dispatch and resumes once; the counter stays1.
This tests the controller's return boundary, not COW numerical restart, power loss,
OS sandboxing, or a complete real CLI/tool adapter. Other tests cover reverse
returns, duplicate/conflicting values, wrong operation/type, shared-ID rejection,
resource settlement, detached views, stale facades and injected sync failures.

## Still to integrate

One production step/run interpreter and CLI must use this controller with the
canonical .bw parser/operation registry, grants, relevant-state plans, budgets,
existing COW client and Executor. Model-selected read/edit/execute/observe/finish
must use those same transitions. General browser actions, verification/adoption,
nested structured contracts, cancellation/abandonment, tail-repair policy,
large-log pressure and full lifecycle/native recovery remain incomplete.
No H07-H12, Ubuntu baseline or original VC/G gate is passed by these tests.

New admissions retain the owner's1024-token thinking default. Recorded512-token
successes are unchanged. Natural thinking cutoff and broad model data collection
remain deferred. All execution is Linux; chat OFF, Q8 deferred, private box-git.

A FLOW can finish only while Ready, after any waits have resumed. A nested FLOW
then returns through the same parent/epoch/slot binding. A registered tool cannot
use finish to pretend it executed; it must follow dispatch/result/settlement.
Completing a FLOW returns a typed value, not a claim that protected verification
passed. Identical finish is idempotent; conflicting values fail. Tests cover
nested completion, refusing premature closure and reopening a finished root.

The earlier SlotReturns transport-checking utility has no production callers in
branchwrite/tools/validation. The new interpreter must use FrameKernel as its
sole workflow return authority, not maintain both as synchronized state stores.
