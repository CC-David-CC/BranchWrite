# BranchWrite (BW)
## First-Principles Architecture Specification

**Version:** 0.5  
**Command:** `branchwrite`  
**Status:** Proposed replacement system contract. This document does not claim an implemented or tested system.
**Scope:** A durable, typed execution runtime with native persistent model contexts. The retained v0.4 input is historical, not a second active specification.

> Explore alternatives in model context. Perform authorized work in isolated execution environments. Accept results from evidence. Preserve the relationship between all three.

## 1. Purpose

BranchWrite is a local, durable, typed execution runtime for programs that use models and computer tools to complete software and computer tasks. It turns an objective into explicit proposals, bounded actions, observations, and checked results. It can explore several approaches without confusing their histories or allowing their unfinished work to interfere.

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

### 2.7 Calls have typed returns, not disappearing text

Every admitted computation has explicit input bindings, an output contract, an owning scope, a continuation destination, and retained provenance. A child can finish execution without its parent yet having accepted the result. A generated title, a summary, an implementation proposal, and a tool execution use this same call/return discipline. They are not hidden helper requests outside the runtime.

### 2.8 Leaving active execution does not erase history

A logical frame can retire from the active execution projection only after its return or terminal disposition is durably recorded and its resources are settled or explicitly transferred. The original node and events remain at their original causal location. A completed/history view references them; it does not move or copy them into a competing tree.

### 2.9 Type, provenance, commitment, and authority are independent

A value's schema describes its shape. Provenance describes who produced it and from which inputs. Commitment identifies which bytes are durable. Authority determines which transitions or effects those bytes may justify. A well-typed model-generated test report is still a model claim, not an observed test result. None of these dimensions may be inferred from a reassuring field name or a boolean supplied by a model.

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

The workflow syntax is a versioned program definition. Its runtime invocation graph records calls of that program, including repeated calls of the same syntax node. A continuation projection records live program counters and pending return slots. COW holds inference state. These are necessary distinct domains, related by explicit identities rather than synchronized duplicate transcripts.

There is no single global last-in/first-out stack under parallel execution. Each sequential call chain behaves like a stack; concurrently active call chains form a frontier. Retained call ownership is a forest rooted in the run, and causal/result edges can form a DAG. UI selection and wall-clock completion order do not establish ownership or data visibility.

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

### Operation definitions and typed values

An operation definition fixes its stable identity and version, input and output types, input-selection rules, allowed effects, error outcomes, and implementation or prompt-template identity. `ASK` specializes such a definition for generation; `DO` specializes one for execution. A workflow procedure composes definitions through the existing verbs. Definitions are pinned when admitted; editing a template or implementation never retroactively changes an existing invocation.

Runtime records are explicit tagged typed values with strict boundary validation. A Python implementation may use TypedDict/Literal definitions and generated validators, or an equivalently enforced single schema source; annotations alone are not the check. Do not accumulate hand-maintained incompatible prompt, runtime, and serialized schemas. Keep values as structured data until a real text or byte transport boundary needs encoding. Serialization is not permission to coerce everything to strings.

Required distinctions include missing versus null, boolean versus integer, text versus bytes, decimal or arbitrary-precision values versus lossy floats, and service-scoped identifiers versus ordinary names. Reject duplicate object keys, unsupported schema versions, non-finite numbers where forbidden, and unknown union variants. Empty lists and empty byte streams can be valid values. Raw tool output is not automatically an instance of a report schema merely because it resembles JSON.

A retained value reference identifies its schema/version, immutable payload digest, producer invocation/event, and source lineage. Provenance and access scope are derived from verified ledger bindings rather than accepted from model-authored metadata. Binary content is an immutable byte artifact; models receive only supported modalities or explicitly described observations. A textual hash is not a capability to read its target.

### Invocation frame

A durable logical frame identifies one invocation, not a CPU stack frame or a COW message. It binds:

- run, task, attempt, invocation, parent scope, and immutable operation/program identities;
- typed argument and local-value bindings and their permitted causal inputs;
- exact program counter, loop iteration, continuation epoch, and next resume location;
- output schema and explicit terminal error/cancellation contracts;
- pending child/native/effect/human wait identities and target result slots;
- model-context reference when needed, workspace/resource bindings when needed;
- grant references, retained results, and resource/budget obligations.

A frame for a file observation does not require a model context. A summary does not require a writable code worktree. Optional resource bindings represent real absence, not hidden fallback behavior.

The runtime must represent these four control situations without contradictory flag combinations:

1. **Ready:** a bounded local transition is possible at the recorded program counter.
2. **Waiting:** the next transition requires identified child, native, effect, or human evidence. Unresolved operations remain here with their reason and retained obligations.
3. **Settling:** a body outcome exists, but owned child/resource cleanup or an authorized ownership transfer is not complete.
4. **Closed:** a typed return or terminal error/cancellation is recorded and all scope obligations are settled or explicitly transferred.

These are frame-control states, not synonyms for task acceptance, model turn state, or publication status. The reducer derives them from events. For a scalar leaf with no cleanup, result commitment and closing may occur in one validated transition.

### Continuations and return slots

A continuation is ordinary durable data, not a Python closure, serialized stack, or unrecorded callback. It names a parent invocation, its attempt and continuation epoch, a wait-set identity, a result-slot name, the accepted type, and the resume location. Expected child identity and result identity are checked before binding. The scheduler allocates these identities; the model cannot choose a trusted parent destination.

Each child can deliver one terminal result to each specifically declared return edge. A duplicate delivery with the same identity and digest is idempotent. A conflicting result for an already bound slot, a result from a cancelled/superseded attempt, or a type mismatch is a recorded error; it cannot silently overwrite the slot. A child result can be retained for inspection even when no longer eligible for consumption.

An unresolved effect is not an ordinary failed return which releases resources. Independent work may continue, but dependent frames remain waiting until reconciliation or an explicitly authorized ownership transfer. A diagnostic report may describe uncertainty without falsely closing the underlying obligation.

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

### Execution kernel, not an endpoint catalogue

BW's center is a typed program transition, not a request handler. Its conceptual operation is:

```text
validated event + reconstructed active frames + immutable definitions
    -> next recorded transition and explicitly authorized dispatch intent
```

HTTP, local functions, a CLI, and event streaming are boundaries around that kernel. Adding a headline or summary must not create another controller, transcript owner, timer loop, or retry policy. It is another admitted invocation of the same `ASK` mechanism with a different input/output contract. No hidden generation is allowed in a status renderer or logger.

Pure projections can render retained data without creating a model invocation. When the scheduler needs an LLM to produce new wording, that work is explicitly admitted, budgeted, recorded, and returned through the same runtime.

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

### Composition and user-facing generations

The seven verbs and six structural constructs are unchanged. Calls, returns, waits and result bindings are interpreter semantics, not extra workflow verbs. A named FLOW has declared inputs and outputs; invoking it creates a frame. REPEAT creates distinct iteration/invocation identities; it cannot overwrite a previous return. ON uses an explicit typed signal and handler scope; it cannot broaden grants, erase errors, or recurse without consuming the inherited budget.

These standard operation definitions are required in the first complete product:

| Operation purpose | Typed result | Application |
|---|---|---|
| Task headline | `Headline` | Display annotation referencing the exact task revision |
| Progress narration | `StatusNote` | Human-readable explanation of a retained status snapshot |
| Evidence summary | `EvidenceSummary` | Structured findings, sources, omissions, and unresolved items |
| Design | `DesignProposal` | Input to design validation, never acceptance by itself |
| Builder decision | `BuilderDecision` | Typed finish, tool request, child-work request, question, or blocker |
| Reasoning note | `ReasoningNote` | Explicit generated analysis, not claimed hidden native reasoning |
| Final response | `FinalResponse` | A user-facing account tied to accepted and unresolved evidence |

Definitions and templates for these purposes must be editable local data, pinned into each run/invocation, not hardcoded scattered prompt strings. All use the same native generation driver. A special purpose does not receive special execution privileges.

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

### Scoped generation and parent resumption

A child generation receives a declared immutable input frontier. For a temporary title or summary, use a separate authorized context branch or an explicitly initialized context from selected artifacts. The choice is declared by context ownership and service placement, not a hidden retry fallback. Do not append housekeeping prompts to the Builder's main context and then try to delete them afterward.

Fork only from a source-pinned eligible committed snapshot. If the required parent branch is in an unresolved mutation, do not improvise a fork from an in-flight head. An already selected independent input root may be used only under its separately admitted lineage; otherwise the child waits or reports the source unavailable. Returning a child value changes the parent's typed binding when allowed; it does not append the child's entire model transcript or merge KV state. Supplying the returned value to a parent's model is a separately recorded stopped-turn input operation when the procedure requires it.

Local frame retirement does not delete canonical native history. Release numerical-context resources only through qualified service operations and retention rules. Unavailable historical checkpoints remain an explicit limit. A runtime frame is not a promise that numerical checkpoint memory is pinned forever.

### Typed tool requests without pretending the transport is stateless

A committed stopped model turn can return a strict `BuilderDecision.request_tool` value. BW validates the nominated tool definition and arguments, builds and authorizes the ordinary plan, and invokes the tool in a child DO/LOOK procedure. The resulting typed observation is returned to the waiting workflow and supplied to the owning model branch as labeled input. The BW workflow remains active across these stopped model turns. No adapter performs an invisible autonomous tool loop.

A native tool-yield protocol can later implement the same semantic boundary only after qualification. The current text-only profile does not require such support and must not claim to have it. Merely recognizing a tool-looking string in provisional output is never a tool call. Stable correlation IDs link the committed request, validated plan, grant, child invocation, execution receipt, typed tool result, and exact result delivery to the model.

### Thinking, channels, and model controls

The runtime must retain distinct typed stream items for native reasoning text when actually exposed, native reasoning summaries when actually exposed, ordinary generated analysis, commentary, final text, and executable proposals. Do not equate these channels. A reasoning fragment is output data, not an instruction to dispatch a tool.

The source-pinned native profile declares supported channel framing, generation/stop semantics, and supported reasoning or sampling controls. Record requested and actually accepted settings. Unsupported controls are rejected or explicitly reported unavailable; never silently label a plain-text generation as a verified native reasoning channel. A visible `ReasoningNote` generated from a prompt is useful, but must be labeled generated analysis rather than recovered hidden reasoning.

For a text-only profile, parse only the explicitly qualified final-envelope/framing contract. Do not strip arbitrary `<think>` sections using a guessed regex. If channel boundaries are unavailable, retain ordinary text and the absence of structured channels. Raw native reasoning is conditional on actual service capability; verifying and reporting that capability is mandatory.

Streaming records bind invocation, native operation, item/channel and ordered segment identity. Reconnection must not double-append chunks. A committed segment can still belong to an active assistant turn. A generation function returns only when the output contract and required turn boundary are satisfied. Durable stream evidence and provisional display buffers remain distinguishable.

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

### One typed decision envelope

An admitted Builder procedure declares a result union such as:

```text
BuilderDecision =
    finish(FinalResponse)
  | request_tool(ToolRequest)
  | request_children(BoundedChildWork)
  | ask_user(UserQuestion)
  | blocked(Blocker)
```

These are proposed data variants, not automatic workflow transitions. The interpreter validates a complete committed value, invokes the existing PLAN/DO/LOOK/CHECK operations or human wait required by that variant, then returns evidence to the owning procedure. Tool requests do not smuggle in new tool definitions or permissions. Child requests do not choose arbitrary parent continuations. Human questions enter a recorded wait and an answer returns to its exact still-live slot; input is not injected into an unrelated active context.

The initial ordered action list remains ordered. A procedure can make successive tool requests or invoke a bounded child procedure through this same mechanism. It must not create a second parallel dispatcher inside an action list.

### Template binding

A generation definition contains a prompt-template identity/hash, declared input slots/types, output schema identity, role binding, model-profile requirements, visibility selector, and failure/return contract. The exact rendered prompt, input artifacts and native context root are retained as private evidence. Role, task content, tool observations and host authority occupy explicitly different fields.

Template expansion is one-pass substitution of declared fields. Values are data and are never recursively expanded, evaluated as code, or interpreted as new template syntax. Missing fields fail before inference; unknown fields do not silently become instructions. JSON output descriptions must be generated from the same canonical type contract used by validation. Updating a template creates a new definition identity; existing calls, partial turns, and original-request retries keep their pinned bytes.

Semantic validation and provenance checks occur after shape validation. Structured output does not make a summary correct, a model status authoritative, or a model-authored verification report observed evidence.

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

### The execution record and its projections

The one ledger must reconstruct definitions used, invocation ownership, typed input/local/result bindings, continuations and waits, stream items and commitment, tool call correlation, resource obligations, and completed history. Materialized indexes are disposable and cannot be separately edited to change execution state.

A minimal conceptual call trace is:

```text
invocation_admitted       exact definition, inputs, parent scope, return edge
wait_registered           parent wait-set/slot and continuation epoch
native_intent             original operation identity and request bytes
native_committed          returned receipt; actual turn state
value_validated           payload schema plus producer and source identity
invocation_returned       terminal value/error, closed scope, eligible slot binding
parent_resumed            next program counter when required waits are satisfied
```

These names illustrate semantics, not mandatory wire names. Admission and wait registration must be one atomic logical ledger transition or an equivalently recoverable transaction so a crash cannot dispatch an orphan child. Return and slot binding must likewise have one logical success point. Artifact publication precedes the transition referencing the result. Parent dispatch happens only after its eligible resumption is recorded.

The live stack/frontier view shows unresolved frames. The completed/history view shows retained invocations and results. The annotation/evidence view references the same result and source IDs. No node is copied into another authoritative tree on return, and no historical parent edges are rewritten. Retained output bytes may be deduplicated by content without deduplicating distinct invocations.

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

### Returning and unwinding a scope

A child does not simply `pop()` because text or a process ended. It must establish its outcome, validate its declared result, retain that result, settle owned resources/children or explicitly transfer them, and commit the applicable return edge. The parent verifies child identity, slot, type, attempt/epoch, and join rule before resuming. Returns do not replay effects.

Unwinding after error, denied authorization, cancellation, or budget exhaustion follows the same scope accounting. A declared handler can consume a typed error result. It cannot infer non-execution from a lost receipt. Pending services and native operations remain owned until observed termination or recorded transfer. A retained diagnostic explaining unknown state does not retire the unknown operation.

Sequential calls resume their immediate declared continuation. Parallel children fill individually named slots. After the wait/join rule is satisfied, one recorded transition makes the parent eligible exactly once. An epoch identifies that wait instance; late results from an earlier retry cannot fill new slots. Already filled sibling slots do not invalidate otherwise valid out-of-order siblings. Do not compare every callback with a mutable global parent revision in a way that rejects the second legitimate sibling.

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

Child results retain declared names and types independent of completion order. Planning joins create an explicit typed aggregate or selected result. They do not concatenate arbitrary return text or use the last completed child as an implicit winner. The call owner and wait set are durable before launching children, and a restarted scheduler obtains the same unresolved frontier from the ledger.

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

Result slots distinguish a proposal, an observed execution outcome, a verified candidate, and a published result. A child delivering a schema-valid `CandidateResult` does not by itself deliver `AcceptedPublication`. Scope return and group success are gated by their declared acceptance/publication obligations. These semantic types share the one invocation mechanism; there is no separate task tree for tools.

## 15. Rewind, branching, and external reality

BW never offers one ambiguous operation that pretends to rewind everything.

A model rewind changes a COW branch's context position. A new task attempt selects a causal starting point without erasing the ledger. A code restoration creates or changes a physical workspace through authorized actions. None of these automatically rewinds threads, sockets, running processes, external transactions, or hardware.

An attempt that changes model context must still bind a truthful physical base. If code and model assumptions no longer agree, BW must supply current observations or establish an appropriate new context before relying on the result.

Rewind and fork are prohibited while the relevant context mutation remains unresolved. Historical branches referenced by active work cannot be silently repurposed. Exploring an older point normally creates a new attempt and context branch so the original evidence remains attributable.

A return to a parent is not a COW rewind. Retiring a child frame changes the active execution projection; it does not move either model head. A retry gets a new invocation/attempt identity, while exact recovery retains the original operation identity. Branch navigation and terminal UI selection never change which continuation receives a result.

## 16. Threads, services, networking, and budgets

The durable unit of work is a task attempt, not a thread. Scheduler threads and asynchronous jobs are implementation mechanisms. Their in-memory stacks, locks, file descriptors, and socket handles are not restored from model snapshots.

A generated program can use internal concurrency within its granted process limits. Its ten threads are not ten workflow branches. They remain part of one managed execution unless the workflow explicitly creates separate tasks.

Managed programs have logical execution identities distinct from PIDs. On restart, BW establishes whether a surviving process actually belongs to the retained execution before observing, signaling, or adopting it. The same PID number is insufficient evidence.

Cancellation stops new scheduling, signals managed work through the execution backend, and observes what terminated. Closing a client connection does not prove that a remote inference operation or service stopped. `STOP` must report any surviving or unresolved work and retain the necessary resource/recovery obligations.

Inference traffic and task networking have separate grants and credentials. Permission for BW to contact a COW service does not authorize task code to contact that service or arbitrary hosts. Public listeners and external writes require explicit capabilities. Network observations record endpoint identity and bounded evidence without leaking credentials.

Every run has a total resource budget. Child allocations consume the parent's allowance rather than creating new unlimited allowances. Limits cover elapsed time, model operations and generated tokens where measurable, context retention, concurrent branches, processes, memory, disk artifacts, output, and network resources. A shared COW service also has one shared scheduling limit regardless of how many roles use it.

Local admission limits and OS-enforced limits must be distinguished in status and evidence. When remote work remains unresolved, BW cannot silently declare its capacity released and reuse that allocation as though termination were confirmed.

Structured scope ownership applies to auxiliary generators too. A title/status child can run concurrently with implementation under a run-owned annotation scope, referencing its target task without making the target wait for presentation work. The run still accounts for that child's eventual completion, cancellation or unresolved operation. This is ordinary ownership and dependency data in the same runtime, not a background title daemon.

A status generator failure has the declared presentation-error disposition and does not change a verified code outcome. Conversely, its successful wording cannot turn a failed tool into a success. All auxiliary inference consumes the same conserved budgets and service admission limits. Prevent self-triggering generation loops through explicit program dependencies and source-frontier triggers: generating a status note does not schedule another status note merely because an event was written.

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

### Required first-product interaction features

The initial product includes task headlines, a factual status view, model-generated progress notes, reusable generation templates, evidence summaries, explicit generated analysis, typed tool interactions, final-response generation, and nested call inspection. These are required capabilities, not an unspecified later UI layer.

Factual status is deterministically projected from retained state: what is running, waiting, verifying, cancelled, failed, accepted, or unresolved. A model-generated StatusNote is a separate dated annotation tied to an exact source frontier. It cannot set factual status. Older notes remain historical and must not replace a newer revision's note simply because they arrived later. User-renamed titles follow explicit user-input events and cannot be silently overwritten by a delayed generated title.

A summary records its target scope, source frontier, source artifact references, findings, omissions and unresolved items. A narrative summary never replaces raw evidence, granted authority, pending tool calls, live resources or exact continuations. A checkpoint/input condensation must preserve required typed bindings and obligations outside the prose. Switching a model to a condensed input creates an explicit new context lineage when required; it is not an invisible rewrite of native history.

Every generated display artifact is traceable to its template, inputs, role/profile, context/native receipts, validation, and return event. No inference is triggered by `show`, `tree`, resizing or rereading a view. Status-generation scheduling is explicit and coalesces redundant source-frontier requests without discarding real failures. Different purposes can use the same model, service and generation function while receiving different scoped inputs and output types.

The interface can display nested active frames, retained completed calls, causal links, typed values, exact pending return destinations, source freshness, and native commitment boundaries. Approval and user-question answers use recorded typed messages addressed to the right invocation. Submit/steer input only at a safe admitted boundary; never splice it into an unresolved native mutation.

## 18. Initial implementation shape

The initial implementation should be one local application with file-backed state, a typed continuation kernel, and a small explicit composition root. A standard-library Python implementation is a suitable baseline; the domain contract does not require a particular language or a central service.

Suggested responsibilities:

```text
branchwrite/
  language.py       immutable workflow syntax and validation
  domain.py         typed definitions, values, frames, continuations, task/plan/evidence identities
  interpreter.py    typed call/return, transitions, scheduling, signals, and budgets
  records.py        ledger, immutable artifacts, and recovery scans
  cow.py            native context operations and exact request recovery
  execution.py      checked filesystem/process/network operations
  workspace.py      candidate workspaces, integration, and publication
  policy.py         grants, capability checks, and acceptance evaluators
  cli.py            command parsing and projections; no hidden generation
  templates/        pinned declarative operation prompts and output contracts
```

These are responsibility boundaries, not a demand for extensibility frameworks. Combine small modules when that improves clarity. Add an execution implementation only when a concrete capability requires it. Do not add an independent transcript database, distributed scheduler, plugin marketplace, or mandatory background daemon to satisfy the initial contract.

Platform-specific enforcement belongs in execution and storage adapters. Shared workflow semantics remain the same. A backend advertises only guarantees established by its conformance tests.

## 19. First complete workflow

The first useful implementation is a genuine typed nested coding session, not only a linear action runner. It must exercise the complete runtime before claiming a usable first release:

```text
run scope
  main task -> LOOK/SAVE immutable project and typed inputs
    Cartographer -> ASK design, CHECK/SAVE validated result, return DesignProposal
    Builder procedure
      ASK decision -> committed request_tool
      PLAN/grant -> child DO/LOOK actual test/tool -> typed ProcessResult
      return tool evidence to the exact waiting Builder procedure
      ASK next decision -> proposed correction
      PLAN/grant -> child DO real file edits
      LOOK/SAVE candidate and CHECK protected acceptance
      return verified candidate
    DO guarded publication when required
    ASK evidence summary and final response -> typed returned values
  annotation work -> ASK headline/status note on isolated selected inputs
```

The program uses the same seven verbs and structural operations throughout. Every generation, tool request/result, wait, continuation, derived summary and final display artifact is retained with typed inputs/outputs. A title or summary must not pollute the coding model's context. Every tool result must go to the correct call. A completed child disappears from the active frontier, not from history.

Interrupt after a child result becomes durable but before parent resumption. Reopen and reconstruct the same pending continuation and typed values. Resume once without repeating the tool, regenerating the child output or losing its native receipt. A real llm-60 campaign must exercise this behavior through the product, not through a competing fixture loop.

When a test fails, the next attempt receives the actual failure evidence and relevant source state. The previous attempt is retained. When no valid action is permitted, BW stops or blocks with the unmet precondition rather than expanding its own authority. Auxiliary presentation errors remain visible without manufacturing a task failure or success.

Next prove parallel planning, parallel execution and integration through the same frames, return slots, records, execution boundary and acceptance mechanism. Reverse child completion order, cancel a waiting parent and submit a late result, preserve unknown effects, and test identical role semantics on one and two actual COW services.

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

### Mandatory typed-runtime and feature coverage

The catalogue must also test named nested returns, exact type round-trips, parent/child argument isolation, non-substitutable provenance, wrong-slot/wrong-epoch rejection, duplicate delivery, retained completed history, durable resume locations, partial generation without premature return, parallel return slots, cancellation/unwind, and resource accounting. A call cursor alone is not this coverage.

Required generator cases cover pinned template/input/output bindings, one-pass rendering, real headline/status/summary/final generation, factual status independence, stale completion handling, user title edits, scoped context isolation, no inference from views, summary omissions/provenance, and explicit context reconstruction. Tool cases cover typed request/result correlation and multi-tool interaction through the one runtime. Thinking cases cover exact native capability reporting, channel/provisional/commit separation, supported controls, explicit generated analysis, and no fabricated native reasoning when unavailable.

Capability discovery can establish that raw native reasoning is unsupported. It cannot be relabeled as a successful native reasoning-stream test. Text-based generated analysis, typed ordinary tool interactions, title/status and summary capabilities still require their own actual acceptance evidence. No claim of feature parity with an unspecified external product is part of this specification.

## 21. Final contract

BranchWrite must maintain one coherent relationship among intent, model context, authority, physical work, and evidence.

It must be possible to inspect an accepted result and identify the exact contract, inputs, model operations, authorization, changes, checks, and publication that produced it. It must be equally possible to inspect a failed or uncertain attempt without losing its history or pretending that nothing happened.

> One local interpreter. Independent model-context branches. Explicitly scoped physical execution. Immutable evidence. Acceptance tied to the exact result. Recovery that preserves uncertainty until the world resolves it.


A call returns a typed, provenance-bound value into one eligible continuation. Its active scope retires only when obligations are settled; its full causal history remains. Headlines, status notes, summaries, thinking output, tool calls and final answers are subjects of this same rule, not exceptions around it.
