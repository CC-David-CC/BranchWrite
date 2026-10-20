# BranchWrite (BW)
## First-Principles Architecture Specification

**Version:** 0.4  
**Command:** `branchwrite`  
**Status:** Proposed system contract. This document does not claim an implemented or tested system.

> Explore alternatives in model context. Perform authorized work in isolated execution environments. Accept results from evidence. Preserve the relationship between all three.

## 1. Purpose

BranchWrite is a local system for completing software and computer tasks with model assistance. It turns an objective into explicit proposals, bounded actions, observations, and checked results. It can explore several approaches without confusing their histories or allowing their unfinished work to interfere.

BW must answer five questions for every consequential operation:

1. What objective does this operation serve?
2. What exact inputs and assumptions does it depend on?
3. What authority permits its effects?
4. What actually happened?
5. What evidence permits the next step?

A model supplies proposals. BW controls execution and acceptance. The operating system and external services perform the actual work. A statement that work succeeded is not evidence that it did.

## 2. Foundational rules

### 2.1 A proposal is not an action

Generated text has no execution authority. Code, shell commands, URLs, plans, and claimed results remain data until BW validates their meaning and authorizes an operation against known resources.

### 2.2 History is not the current world

A saved event records a past decision or observation. A file, process, service, or remote account may have changed since that event. Before using a historical observation as a current precondition, BW must establish that it still applies.

### 2.3 A branch needs an explicit scope

A branch identifies a line of work and its permitted evidence. It is not automatically a copy of a computer. Model context, task history, files, and live resources have separate ownership and separate branching mechanisms.

### 2.4 Acceptance follows evidence

A task is complete only when its acceptance contract has been satisfied. Model confidence, a clean process exit, or an attractive explanation cannot replace missing checks. Passing checks establish the tested conditions, not unlimited correctness.

### 2.5 Uncertainty must remain visible

A lost connection can leave an operation committed, unfinished, or unknown. BW must retain that uncertainty until it obtains enough evidence to resolve it. It must not manufacture certainty by silently repeating the operation.

### 2.6 One authority controls progress

One local interpreter controls task transitions, scheduling, authorization, and acceptance. Models, execution workers, and interfaces return proposals or observations; they do not independently advance workflow state.

## 3. Roles and deployment

BW has two logical model roles.

| Role | Responsibility | Typical result |
|---|---|---|
| **Cartographer** | Understand the objective, expose assumptions, design alternatives, and propose task decomposition and checks. | A design or bounded task proposal. |
| **Builder** | Propose concrete changes, inspect supplied evidence, and revise implementation approaches. | An action proposal or explanation of a blocker. |

Neither role owns a separate execution loop. Neither can authorize its own effects or declare a task accepted.

Role names do not specify hardware, model size, or deployment. The roles can use two Context COW services, one shared service and model, or different configured services for different tasks. Each active role instance has its own context branch and declared inputs. Sharing a service does not mean sharing role-specific history.

The local interpreter executes computer operations on its configured execution host. An inference server is not an execution host merely because it generates code. Remote execution requires an explicitly configured execution capability and the same authorization, observation, and recovery contract.

Example deployment configuration:

```json
{
  "schema": "branchwrite.routes.v1",
  "services": {
    "a": {
      "url": "http://127.0.0.1:18080",
      "credential_env": "BW_COW_A_KEY"
    },
    "b": {
      "url": "http://127.0.0.1:18081",
      "credential_env": "BW_COW_B_KEY"
    }
  },
  "roles": {
    "cartographer": {"service": "a"},
    "builder": {"service": "b"}
  }
}
```

Binding both roles to `a` changes placement only. It must not change task semantics, effect permissions, or evidence requirements. These loopback addresses are configuration examples, not discovered endpoints.

## 4. What the system owns

Each domain has one authority. BW relates domains through explicit references rather than pretending they are one interchangeable state.

| Domain | Authority | BW retains |
|---|---|---|
| Task decisions and authorizations | Local causal ledger | Events, causal parents, policy decisions, and attempt identities. |
| Model context and turn state | The owning COW service | Service binding, namespace, branch, snapshot, revision, operation identity, and receipts. |
| Exact retained bytes | Immutable artifact store | Content hashes and metadata referenced by events. |
| Candidate code | Its execution workspace | Base revision, workspace identity, changes, and observed snapshots. |
| Accepted code | A configured published Git reference | Accepted commit and publication receipt. |
| Processes, sockets, devices, and remote state | Their actual operating system or service | Logical resource identity, live observations, and recovery obligations. |

The displayed tree and task status are projections of retained events. They are disposable and must be rebuildable. Model history may be fetched for display or retained as operation evidence; a local display cache must never become a competing authority for COW state.

The task decomposition is a tree. Causal history can have several parents at integration points and is therefore a directed acyclic graph. A task node, a COW branch, and a Git worktree are different objects even when the interface displays them together.

## 5. Minimal domain objects

### Task contract

A task contract fixes the objective, required inputs, permitted effects, acceptance criteria, dependencies, and budget. It identifies protected requirements that a model cannot alter.

Cartographer may propose additional checks or a revised contract. Replacing required checks or broadening authority requires a separately recorded authorized decision. A failed attempt cannot weaken its own definition of success.

### Task node and attempt

A node is a bounded responsibility in the task tree. An attempt is one execution of that responsibility against specific inputs. A new approach, changed input base, or deliberate regeneration creates a new attempt rather than rewriting the previous one.

An attempt binds its contract, role, visible causal head, input artifact hashes, COW context reference, workspace reference, and remaining budget. Mutable status is derived from events rather than independently edited in another state file.

### Proposal, plan, and authorization

A proposal is model-produced data. A plan is a validated immutable description of executable work bound to actual inputs and resource preconditions. An authorization is permission for that exact plan under a defined capability scope.

These are distinct because validity does not imply permission, and permission does not establish success.

### Observation and acceptance

An observation is evidence obtained at a real boundary: inspected bytes, a process result, a service receipt, or another recorded measurement. Acceptance is a deterministic check result or an explicitly required human decision based on identified evidence.

A model's claim and an observed fact must remain distinguishable in records and displays.

## 6. System structure

```text
                         CLI / tree display
                                |
                       Local BW interpreter
                       /        |         \
                 CowClient    Ledger    Effect executor
                  /    \       +            |
          Cartographer Builder artifacts   Workspaces
                  |    |                   Processes
                COW services              Files / IPC / network
```

The interpreter contains workflow semantics and policy decisions. The COW client implements native context operations. The executor implements authorized computer effects. The ledger stores local intent and evidence. The interface submits requests and presents projections.

The scheduler belongs to the interpreter. Workers may wait on I/O or run processes concurrently, but only the interpreter's journal writer records accepted state transitions. No worker obtains workflow authority by completing first.

## 7. Workflow language

### Domain verbs

| Verb | Meaning |
|---|---|
| `ASK` | Request an answer or proposal from a bound model context. |
| `PLAN` | Validate a proposal and freeze executable work against observed inputs. |
| `DO` | Execute authorized work through the checked effect boundary. |
| `LOOK` | Obtain bounded observations of relevant resources or retained results. |
| `SAVE` | Promote selected results and evidence into named retained artifacts. |
| `CHECK` | Evaluate evidence and apply an explicit disposition. |
| `STOP` | End the flow deliberately and account for outstanding work. |

`ASK` is not necessarily one network exchange. A logical answer can require multiple native continuation operations. Each operation remains separately identified and budgeted.

`LOOK` means observation, not unrestricted execution disguised as a read. A test program that writes caches, launches processes, or opens sockets runs through `DO`; `LOOK` inspects its result. Read capabilities are bounded because observation can expose private information or contact an external system.

`SAVE` is not the point at which BW first becomes durable. The interpreter automatically records dispatch intent, receipts, authorization, and unresolved effects. `SAVE` expresses that a result is being retained for subsequent reasoning or acceptance. Skipping or failing to reach `SAVE` cannot erase an action's recovery record.

`CHECK` uses registered evaluators with explicit outcomes. It may accept, reject, select candidates, request approval, or emit a named signal according to the frozen contract. Checks that require programs or network operations use planned effects and evaluate the resulting evidence. A model-generated command is not itself a trusted evaluator.

### Structural operations

| Operation | Meaning |
|---|---|
| `FLOW` | A named ordered composition of work. |
| `REPEAT` | A bounded repetition with an explicit exit condition and exhausted-budget disposition. |
| `BRANCH` | A child line of work with declared inherited inputs and independent subsequent history. |
| `PARALLEL.PLAN` | Concurrent planning against one immutable physical base with independent causal/model histories. |
| `PARALLEL.DO` | Concurrent execution with isolated physical workspaces and controlled shared resources. |
| `ON` | A local handler for a declared signal, subject to normal authorization and budget rules. |

Constructing or displaying a workflow performs no inference and dispatches no task effects. The workflow is immutable syntax. Model-proposed decomposition becomes executable only after validation under the parent contract, including depth, fan-out, dependency, and budget limits.

Both a one-branch task and a parallel task use the same execution path. Parallelism changes dependencies, workspace allocation, and scheduling; it does not introduce another tool protocol.

## 8. Native model-context contract

BW treats a model context as a persistent resource with an owner, identity, revision, and turn state. It sends new input or requests continuation against that resource instead of rebuilding an entire conversation for every request.

The local `CowClient` supports these native operations:

| Purpose | Operations |
|---|---|
| Establish a context | `namespace`, `load`, `prepare` |
| Generate an answer | `ask`, `answer` |
| Add input to a stopped turn | `append-user` |
| Continue an active assistant turn | `continue` |
| Navigate context state | `fork`, `rewind` |
| Inspect state | `status`, `branches`, `history`, `operation` |
| Recover an original request | `retry-request` |
| Finish a retained publication when the service permits it | `retry-publication` |

These are semantic operation names. Implementations must use the actual native wire contract rather than inventing request paths or assuming unverified response fields.

A context reference includes the service binding, namespace, branch, observed revision, and relevant snapshot. Service identity must be tied to the intended backing store and model configuration during qualification; a URL alone is not proof that the same context owner returned after a deployment change. Snapshot identifiers are meaningful only in their owning service.

### Generation has two different completion boundaries

A durable request receipt establishes what one operation committed. It does not necessarily establish that the assistant turn stopped.

When a token-limited operation commits a partial answer and the turn remains active, BW records that receipt and may schedule `continue` under the remaining budget. It must not append another user message to obtain the remaining tokens.

Provisional streamed output may be displayed as provisional. BW does not parse it into executable work. A proposal is eligible for validation only after the required output is committed, the turn has reached the expected boundary, and the complete structured response is available. Malformed stopped output is rejected; incomplete active output is continued or stopped by budget, not silently repaired.

### Operation identity and recovery

Before mutation, BW durably records the service binding, exact request bytes, original expected revision, and operation ID. One context branch may have only one unresolved mutating operation under BW's control.

On a lost acknowledgment, BW reconciles or replays the original request using the same ID and original inputs. It does not silently substitute the current revision. A stale revision remains a conflict requiring a deliberate next decision.

After a service restart, missing process-local operation status does not alone establish non-commitment. BW follows native receipt recovery. Checkpoint eviction or lost unfinished inference may prevent continuation; BW reports that limit rather than claiming that every historical context remains executable.

An explicit reconstruction creates a new context lineage from retained artifacts. It is not silently labeled restoration of the old numerical state.

### Information passed to a role

A role receives the task contract and a bounded selection of permitted inputs. Artifact hashes establish identity, not model comprehension. BW must supply the needed textual content or an authorized retrieval observation; merely naming a local file or hash does not give a remote model access to its bytes.

For the text-generation contract, committed tool observations are supplied as clearly labeled task data through stopped-turn input. They do not impersonate control instructions or confer authority on quoted content. No native model tool-call feature is assumed.

After physical changes, new observations must identify the current workspace revision and supersede stale assumptions explicitly. Inherited context does not make an old repository description current.

Cartographer-to-Builder handoff uses immutable design and evidence artifacts. With different services, each service establishes its own context from those inputs. BW assumes neither cross-service snapshot transfer nor zero processing cost on a second service. With one service, independent role branches may share an authorized project-only prefix.

## 9. From proposal to executable plan

The initial proposal format is strict structured text. BW rejects invalid syntax, duplicate keys, unknown fields, unsupported action kinds, unresolved artifact references, and inconsistent preconditions. It never searches arbitrary prose for something executable or evaluates generated text as host instructions.

`PLAN` binds the proposal to:

- The task and attempt, input artifact hashes, and exact workspace base.
- An ordered sequence of typed actions and each action's resource preconditions.
- Actual required capabilities derived by the executor, not asserted by the model.
- Output obligations, acceptance checks, and resource limits.

Authorization binds the resulting plan hash, policy revision, permitted resources, and applicable expiration or budget. Changing the plan changes its identity. Each action rechecks relevant preconditions immediately before dispatch. Changes made by earlier actions must be accounted for by their observed postconditions; comparing every later action to an obsolete initial file hash would be incorrect.

The initial action sequence is ordered. Concurrency is expressed through the workflow's branch structure, not through a second hidden planner inside an action list.

File-edit actions refer to exact intended bytes or a patch with a required preimage. Process actions specify an executable, argument array, working directory, allowed environment, immutable input references, output limits, deadline, and execution profile. Publication and external transactions require their own explicit effects.

## 10. Execution and capability enforcement

BW performs real operating-system operations. Records describe those operations; they do not substitute for them.

| Capability | Required implementation behavior |
|---|---|
| Files | Scoped reads and writes, checked preconditions, verified result bytes, and controlled path resolution. |
| Programs | Native child processes with explicit arguments, environment, identity, deadlines, and bounded output. |
| Services | Managed process lifecycles, readiness observations, resource ownership, and checked termination. |
| Git | Brokered workspace creation, change inspection, candidate commits, integration, and guarded reference updates. |
| Network | Authorized destinations and operations with explicit credential, response-size, and timeout rules. |
| Sockets and IPC | Real handles with framing, endpoint identity, ownership, and cleanup obligations. |

Generated code is an artifact. Executing it is an authorized process action. It may create threads, spawn children, write files, or open sockets only within the real capabilities of its execution environment.

The executor uses argument arrays by default. A shell script is permitted when it is the explicit approved artifact; invoking a shell does not bypass the effect contract.

### Isolation means enforced boundaries

A working directory is not a permission boundary. A Git worktree is not a complete process sandbox. BW must restrict resource access at the boundary that can actually enforce the required policy.

A qualified execution profile must enforce the required filesystem visibility, write scope, credential exposure, child-process limits, and network access. Path checking must account for links and concurrent replacement. Merely rejecting strings containing `..` is not sufficient.

Untrusted task processes must not be able to rewrite the ledger, artifacts relied on as immutable evidence, policy, protected verification inputs, sibling workspaces, or shared Git administration data. Git metadata mutation is performed through the workspace broker, not implicitly granted to arbitrary candidate processes.

An action is admitted only when its actual authority is contained within its grant and all required restrictions are enforceable. A profile allowing broad host access must say so; it cannot satisfy a narrower isolation requirement by relabeling itself. An unsupported requirement blocks dispatch rather than causing silent degradation.

Policies may preauthorize ordinary scoped work so each file edit does not require a prompt. Broader filesystem access, credentials, installation, privilege changes, deployment, and external publication require the appropriate explicit grant. Models cannot modify those grants through task content.

## 11. Saving and the local record

A run uses an inspectable local layout:

```text
RUN/
  manifest.json
  events.jsonl
  artifacts/
    sha256/<content-hash>
  workspaces/
  scratch/
```

The immutable manifest contains run identity, task contract references, configuration and policy bindings, and implementation version information needed to interpret the run. Configuration secrets are referenced by credential binding, not copied into this manifest.

The event ledger is append-only and single-writer. Versioned records include integrity checks so recovery can distinguish damaged records from valid history. Events identify their run, attempt, causal parents, operation or action identity, referenced artifacts, and disposition. Integrity checks detect corruption; they do not authenticate history against an actor able to replace all of the control state. Ledger append order is storage order, not permission for a sibling to see another sibling's work. Visibility follows causal ancestry and explicit joins.

Artifacts retain exact text or binary bytes: designs, patches, source snapshots, request payloads, receipts, logs, images, archives, and test reports. A derived summary identifies its source artifact and does not replace the raw evidence. Truncation and redaction are recorded rather than silently presented as complete output.

The run directory is private control state outside the writable scope of task execution. Retained inputs and logs may contain confidential material even when credentials are excluded.

### Durable write ordering

BW writes and verifies an artifact before appending an event that references it. The storage adapter stages bytes, establishes the content hash, publishes them without modifying an existing immutable artifact, and performs the durability operations required by its qualified filesystem profile.

Before external dispatch, the corresponding intent event must be durable under that profile. Recovery detects incomplete trailing records and distinguishes them from corruption of previously accepted history. Corrupt or missing committed evidence blocks progress; it must not be silently discarded.

A crash can leave an unreferenced artifact. That is recoverable storage residue, not a successful task event. Garbage collection uses retained references and a declared retention policy; it does not remove evidence needed by unresolved work.

Process-restart recovery and power-loss durability are separate qualification claims. Neither is established merely by producing valid JSON or calling a flush function.

## 12. The effect lifecycle

Every consequential effect follows the same lifecycle:

```text
validated plan + valid grant + satisfied preconditions
                         |
                         v
                durable dispatch intent
                         |
                         v
                 real operation attempt
                         |
                         v
              observation and reconciliation
                         |
                         v
        retained outcome -> checked workflow disposition
```

The intent contains a stable action identity and exact inputs. The executor records what it actually dispatched and what it observed. Exit status is process evidence; it is not automatically evidence that all intended file or remote effects occurred.

BW distinguishes a known success, known failure, and unresolved outcome. A crash after dispatch but before a local receipt does not prove that the effect failed or never started.

Recovery depends on the resource. A file replacement can be compared with its required before and after bytes. A remote operation may have an idempotency key or queryable receipt. A process may be identifiable through its managed execution identity and retained output. An arbitrary remote mutation may have no adequate reconciliation method.

When BW cannot distinguish whether a non-repeatable effect occurred, it blocks dependent work and preserves the uncertainty. It does not promise universal exactly-once execution. Compensation, when possible, is another authorized action with its own evidence; it is not deletion of the original event.

## 13. Parallel planning

`PARALLEL.PLAN` fixes an immutable input set before launching children:

```text
parent causal head E0
physical source snapshot T0
accepted task and evidence artifacts A0
```

Each child sees the permitted ancestors of `E0`, the same source snapshot `T0`, its declared role/task inputs, and its own subsequent events. A sibling's unfinished or completed response is not visible merely because it arrived first.

On a shared COW service, children fork suitable context snapshots. On different services, BW initializes equivalent authorized task inputs without claiming identical model state.

Planning has no authority to mutate the shared project or external systems. Observational programs that need scratch files run in private scratch environments with the source mounted read-only and with bounded effects.

A planning join records the child results admitted by the acceptance contract. Rejected alternatives retain their evidence. Joining results does not merge numerical inference snapshots; it creates a new causal point and supplies selected artifacts as new input where needed.

## 14. Parallel execution and integration

Before any child mutation, `PARALLEL.DO` must allocate an independent candidate worktree and execution scope for every mutating branch. A one-branch execution uses the same mechanism.

The default isolation unit includes its candidate files, scratch space, temporary directory, writable caches, environment, managed processes, and allocated service resources. Shared read-only inputs are allowed. Non-isolatable writable resources must be serialized through an exclusive capability or rejected.

Two branches editing the same relative path in different worktrees is a potential integration conflict, not a shared-write race. Two branches using the same database, port, device, home directory, or shared Git metadata are not isolated by those worktrees.

Resource reservations must be real. For example, selecting a currently unused port and releasing it is not a durable reservation; the execution backend must retain ownership or handle allocation failure before dependent work proceeds.

### Candidate acceptance

Each candidate is inspected and checked against its own plan and required acceptance inputs. Verification evidence binds the exact candidate revision and environment. Verification runs must not allow the candidate source or protected tests to change unnoticed while they are being checked; writable test output goes to designated scratch space.

An accepted candidate that is subsequently edited is a new physical state and does not inherit the old acceptance result.

### Integration selection

The task contract states how candidate results are selected. Complementary required branches must all succeed. Alternative implementations require an explicit selection decision; BW must not merge mutually exclusive alternatives merely because both passed their individual tests.

The selected integration set, its evidence, and its authorization are recorded. Selected candidates are integrated in declared order into a separate workspace. Conflicts become explicit tasks; they are not hidden automatic rewrites. The combined result receives its required integration checks even when each candidate passed alone.

### Publication boundary

BW defines accepted code publication as advancing a configured Git reference to an approved, verified commit, conditional on the reference still matching the expected prior value. This creates one precise publication point.

The publication reference must not be the live branch of an independently managed checkout; BW must refuse that target or establish an explicit exclusive ownership contract. BW does not define publication as a supposedly atomic rewrite of a user's open working directory. Materializing or updating an ordinary checkout is a separate authorized filesystem operation with cleanliness, ownership, and recovery requirements. A checkout that unrelated writers can change cannot be treated as exclusively controlled without an enforceable boundary.

The successful execution join is recorded only after the required publication is confirmed. A lost publication acknowledgment is reconciled against the target reference before retry. A failed group still records all observed outcomes but does not receive a successful join.

## 15. Rewind, branching, and external reality

BW never offers one ambiguous operation that pretends to rewind everything.

A model rewind changes a COW branch's context position. A new task attempt selects a causal starting point without erasing the ledger. A code restoration creates or changes a physical workspace through authorized actions. None of these automatically rewinds threads, sockets, running processes, external transactions, or hardware.

An attempt that changes model context must still bind a truthful physical base. If code and model assumptions no longer agree, BW must supply current observations or establish an appropriate new context before relying on the result.

Rewind and fork are prohibited while the relevant context mutation remains unresolved. Historical branches referenced by active work cannot be silently repurposed. Exploring an older point normally creates a new attempt and context branch so the original evidence remains attributable.

## 16. Threads, services, networking, and budgets

The durable unit of work is a task attempt, not a thread. Scheduler threads and asynchronous jobs are implementation mechanisms. Their in-memory stacks, locks, file descriptors, and socket handles are not restored from model snapshots.

A generated program can use internal concurrency within its granted process limits. Its ten threads are not ten workflow branches. They remain part of one managed execution unless the workflow explicitly creates separate tasks.

Managed programs have logical execution identities distinct from PIDs. On restart, BW establishes whether a surviving process actually belongs to the retained execution before observing, signaling, or adopting it. The same PID number is insufficient evidence.

Cancellation stops new scheduling, signals managed work through the execution backend, and observes what terminated. Closing a client connection does not prove that a remote inference operation or service stopped. `STOP` must report any surviving or unresolved work and retain the necessary resource/recovery obligations.

Inference traffic and task networking have separate grants and credentials. Permission for BW to contact a COW service does not authorize task code to contact that service or arbitrary hosts. Public listeners and external writes require explicit capabilities. Network observations record endpoint identity and bounded evidence without leaking credentials.

Every run has a total resource budget. Child allocations consume the parent's allowance rather than creating new unlimited allowances. Limits cover elapsed time, model operations and generated tokens where measurable, context retention, concurrent branches, processes, memory, disk artifacts, output, and network resources. A shared COW service also has one shared scheduling limit regardless of how many roles use it.

Local admission limits and OS-enforced limits must be distinguished in status and evidence. When remote work remains unresolved, BW cannot silently declare its capacity released and reuse that allocation as though termination were confirmed.

## 17. Stepping, inspection, and interfaces

The initial interface is a local CLI. A richer display may consume the same events and submit the same requests without owning another controller.

Proposed commands:

```text
branchwrite new --repo PATH --task TEXT --routes routes.json
branchwrite show RUN
branchwrite tree RUN
branchwrite step RUN
branchwrite run RUN
branchwrite reconcile RUN
branchwrite verify RUN
branchwrite stop RUN
```

`new` creates local run records but dispatches no inference or task effects. `show` and `tree` inspect retained local state; they do not silently refresh remote services or mutate anything.

`step` advances one bounded interpreter transition. It may dispatch one external operation, consume one completed result, or make one local decision. It never conceals an unbounded generation/tool loop. `run` repeatedly drives the same transition mechanism and can keep independent branches in flight.

A logical `ASK` spanning several generation chunks therefore spans several transitions. A `DO` plan containing several ordered actions also spans transitions. The event schema records the exact operation cursor so restart does not rely on reconstructing an unstated call stack.

`reconcile` obtains authorized evidence about unresolved operations. Native request recovery can complete previously intended work, so reconciliation is not advertised as globally read-only. `verify` schedules necessary observations and test effects through normal policy. `stop` requests controlled termination and reports what remains uncertain.

The display must distinguish proposed, authorized, dispatched, observed, accepted, rejected, and unresolved work without presenting these as interchangeable meanings of “done.” It shows task identity, model branch, workspace revision, and evidence references together while keeping their meanings distinct.

## 18. Initial implementation shape

The initial implementation should be one local application with file-backed state and a small explicit composition root. A standard-library Python implementation is a suitable baseline; the domain contract does not require a particular language or a central service.

Suggested responsibilities:

```text
branchwrite/
  language.py       immutable workflow syntax and validation
  domain.py         task, attempt, plan, evidence, and identity values
  interpreter.py    transitions, scheduling, signals, and budgets
  records.py        ledger, immutable artifacts, and recovery scans
  cow.py            native context operations and exact request recovery
  execution.py      checked filesystem/process/network operations
  workspace.py      candidate workspaces, integration, and publication
  policy.py         grants, capability checks, and acceptance evaluators
  cli.py            command parsing and presentation
```

These are responsibility boundaries, not a demand for extensibility frameworks. Combine small modules when that improves clarity. Add an execution implementation only when a concrete capability requires it. Do not add an independent transcript database, distributed scheduler, plugin marketplace, or mandatory background daemon to satisfy the initial contract.

Platform-specific enforcement belongs in execution and storage adapters. Shared workflow semantics remain the same. A backend advertises only guarantees established by its conformance tests.

## 19. First complete workflow

The first useful implementation must complete a small local code task end to end:

```text
LOOK at an immutable project snapshot
SAVE the task inputs
ASK Cartographer for a bounded design
CHECK the design against the task contract
SAVE the accepted design
ASK Builder for an action proposal
PLAN the exact work against the source snapshot
obtain the required grant
DO in an isolated candidate workspace
LOOK at actual changes and process evidence
SAVE the candidate and observations
CHECK the acceptance contract
DO authorized publication when the contract requires it
STOP with accepted revision and evidence, or an explicit disposition
```

When a test fails, the next attempt receives the actual failure evidence and relevant source state. The previous attempt is retained. When no valid action is permitted, BW stops or blocks with the unmet precondition rather than expanding its own authority.

The next complete increment adds parallel planning. The next adds parallel execution and integration. Both reuse this workflow's records, execution boundary, and acceptance mechanism.

## 20. Acceptance gates

All cases below are required tests, not reports of tests already run.

### G0 — Meaning and ownership

Verify immutable workflow construction; all seven verbs and structural operations; explicit check dispositions; bounded repeat/decomposition; single-writer transitions; deterministic causal projection; and rejection of proposals that attempt to change policy or mark themselves accepted.

### G1 — Context state

With a real native service, verify initialization, stopped-turn input, active-turn continuation, durable partial receipts, provisional output exclusion, stale revision rejection, original-ID recovery, fork, rewind, and unavailable-checkpoint behavior. Run the same role workflow with one service and with two. Verify no unjoined sibling history leaks into a request.

### G2 — Actual effects

Create and inspect real files; run a real program and retain its output; prove denied writes and denied network operations are actually denied by the selected backend; test link/path escape attempts; protect ledger and verification inputs; and establish descendant-process handling. Do not substitute a mocked permission decision for an execution-boundary test.

### G3 — Durable recovery

Interrupt before dispatch, after dispatch, during output, after remote commit, during artifact publication, and before local outcome recording. Reopen the run and reconcile actual resources. An uncertain non-repeatable effect must remain blocked rather than being executed again. Test partial-tail detection, corruption handling, missing referenced artifacts, and duplicate run writers.

### G4 — Parallel correctness

Verify identical planning bases, causal isolation, separate worktrees, blocked sibling access, private scratch/caches, shared-resource exclusion, integration selection, deterministic merge order, conflict handling, combined verification, and target-reference divergence. Test alternative candidates separately from complementary required branches.

### G5 — Publication and lifecycle

Verify publication receipt recovery; no successful join before required publication; no inherited acceptance after candidate mutation; no implied rollback of external effects; service identity checks after restart; cancellation with surviving work; shared-endpoint capacity; and budget conservation across branches.

### G6 — Usability and platform qualification

Verify that inspection is read-only, step is bounded, run uses the same interpreter, unresolved work is visible, and every accepted result links to evidence. Qualify each intended operating system and storage profile independently. Report native GPU reuse, process restart, power-loss durability, filesystem isolation, and network isolation as separate measured capabilities.

Mocks and scripted services are useful for fault injection. They do not establish the behavior of an untested native service, operating system, execution profile, or device.

## 21. Final contract

BranchWrite must maintain one coherent relationship among intent, model context, authority, physical work, and evidence.

It must be possible to inspect an accepted result and identify the exact contract, inputs, model operations, authorization, changes, checks, and publication that produced it. It must be equally possible to inspect a failed or uncertain attempt without losing its history or pretending that nothing happened.

> One local interpreter. Independent model-context branches. Explicitly scoped physical execution. Immutable evidence. Acceptance tied to the exact result. Recovery that preserves uncertainty until the world resolves it.
