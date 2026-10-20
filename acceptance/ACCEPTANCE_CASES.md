# Product acceptance cases — all not_run

## BW-G6-001 — Exact repository identity
Owner: R01 · boundaries: filesystem, git

Exercise: Inspect origin, head, dirty state, inherited instructions, baseline test entry points and license
Oracle: Report actual facts; do not substitute a different remote or infer an empty repository from failed web retrieval

## BW-G6-002 — Preserve source and unrelated work
Owner: R29 · boundaries: filesystem, git

Exercise: Stage handoff integration in a new path and make a scoped product change
Oracle: Source SHA-256 unchanged; unrelated file and staged state preserved; product remains BranchWrite with branchwrite command

## BW-G6-003 — Baseline failures remain attributable
Owner: R29 · boundaries: filesystem, git

Exercise: Capture pre-edit and post-edit results
Oracle: Existing failure recorded as existing, not erased or reclassified as passing; later fixes have separate evidence

## BW-G1-001 — Actual native wire discovery
Owner: R10 · boundaries: native_cow

Exercise: Read actual request, streaming, revision and recovery implementations; capture native status
Oracle: Source-pinned operation map and trace exist; no invented routes, ordinary inference fallback or claimed API fields

## BW-G1-002 — Service identity differs from URL
Owner: R10 · boundaries: native_cow

Exercise: Resolve role bindings and record identity evidence
Oracle: Model/store/source binding established beyond URL; unchanged alias cannot silently substitute a new owner

## BW-G1-003 — No inference from unbound safety profile
Owner: R28 · boundaries: native_cow

Exercise: Attempt product live admission
Oracle: Dispatch denied before any generation; unknown values are not replaced by guessed ports or unlimited budgets

## BW-G1-004 — Host lifecycle ownership
Owner: R10 · boundaries: native_cow

Exercise: Perform read-only discovery and namespace-scoped tests
Oracle: No unknown process stopped, no global install or model replacement; lifecycle ownership and outstanding resources recorded

## BW-G0-001 — Passive workflow construction
Owner: R02 · boundaries: pure

Exercise: Construct, validate and render without installed model or executor
Oracle: No inference, filesystem mutation or process dispatch; syntax and bound inputs immutable

## BW-G0-002 — Explicit semantic dispositions
Owner: R08 · boundaries: pure

Exercise: Validate flow registration
Oracle: Missing disposition rejected; outcome meaning cannot depend on a default that hides failure

## BW-G0-003 — Bounded decomposition
Owner: R28 · boundaries: pure

Exercise: Validate child tasks against parent contract
Oracle: Invalid trees/dependencies rejected before execution; child authority and budget cannot exceed parent

## BW-G0-004 — Identity domains cannot substitute
Owner: R02 · boundaries: pure

Exercise: Attempt invalid cross-domain bindings
Oracle: Typed validation rejects conflation; identical string values in different services do not imply interchangeable snapshots

## BW-G3-001 — Artifact precedes referencing event
Owner: R26 · boundaries: filesystem, process_restart

Exercise: Persist artifact and referencing event then reopen in another process
Oracle: Hash and bytes verified; no committed event references an unpublished object

## BW-G3-002 — Independent writer exclusion
Owner: R27 · boundaries: filesystem, process_restart

Exercise: Hold writer ownership in one while the other attempts transition append
Oracle: Exactly one writer admitted; rejected process cannot append or change projection

## BW-G3-003 — Binary and output provenance
Owner: R27 · boundaries: filesystem, process_restart

Exercise: Save both and reload their records
Oracle: Exact raw bytes preserved privately; derivative labels and original references retained without pretending completeness

## BW-G3-004 — Projection rebuild
Owner: R27 · boundaries: filesystem, process_restart

Exercise: Delete disposable indices and rebuild
Oracle: Identical semantic state; no independent mutable status file is needed

## BW-G0-005 — Strict proposal syntax
Owner: R02 · boundaries: pure

Exercise: Parse complete stopped proposals
Oracle: Each invalid form rejected without extraction, repair or hidden model request

## BW-G0-006 — No self-authorization
Owner: R02 · boundaries: pure

Exercise: Compile under protected task contract
Oracle: Proposal cannot grant effects or lower protected criteria; illegal fields rejected

## BW-G0-007 — Plan identity binds authorization
Owner: R08 · boundaries: pure

Exercise: Validate altered plan for dispatch
Oracle: Old grant does not apply; plan identity includes exact inputs and actual capability scope

## BW-G0-008 — Sequential postconditions
Owner: R08 · boundaries: pure

Exercise: Validate preconditions at each step
Oracle: Valid chain admitted; stale or unobserved postimage rejected; initial hash is not incorrectly reused for every action

## BW-G0-009 — One bounded step
Owner: R08 · boundaries: pure

Exercise: Advance interpreter one step repeatedly
Oracle: Each step dispatches at most one external operation, consumes one completion or makes one local decision; cursor explicit

## BW-G0-010 — One authority for completion
Owner: R08 · boundaries: pure

Exercise: Apply observations through writer/interpreter
Oracle: Worker completion never directly advances workflow; causal visibility does not follow append order

## BW-G0-011 — REPEAT and ON remain bounded
Owner: R08 · boundaries: pure

Exercise: Drive until exhaustion and signal handling
Oracle: Handler preserves normal grants; exhaustion records explicit disposition; no recursive hidden retry loop

## BW-G0-012 — One sequential/parallel effect path
Owner: R08 · boundaries: pure

Exercise: Compare admitted action/authority semantics
Oracle: Same executor and records; no alternate tool or inference protocol for parallel work

## BW-G1-005 — Native context initialization
Owner: R10 · boundaries: native_cow

Exercise: Execute namespace/load/ask and prepare/answer through product client
Oracle: Actual receipts identify correct roots/turns; inputs match retained intent and no full transcript replay

## BW-G1-006 — Stopped-turn input
Owner: R10 · boundaries: native_cow

Exercise: Append new labeled observation/user input
Oracle: One new input at native stopped boundary with expected revision and committed receipt

## BW-G1-007 — Scoped native read operations
Owner: R10 · boundaries: native_cow

Exercise: Perform native status, branches and history reads
Oracle: Correct owning service and context returned; local display cache is not authoritative

## BW-G1-008 — No conventional inference dispatch
Owner: R10 · boundaries: native_cow

Exercise: Run initialization and follow-up generation
Oracle: Only verified native operations occur; no ordinary completion/response compatibility path or prompt reconstruction

## BW-G1-009 — Provisional output has no authority
Owner: R10 · boundaries: native_cow

Exercise: Supply complete-looking action serialized typed text as observed provisional output
Oracle: Display labels provisional; PLAN and ACT remain inadmissible until committed stopped boundary

## BW-G1-010 — Active partial versus stopped answer
Owner: R28 · boundaries: native_cow

Exercise: Record receipt then continue same turn
Oracle: No new user message; original logical answer composed from committed chunks with separately budgeted operations

## BW-G1-011 — Continuation exhausted budget
Owner: R28 · boundaries: native_cow

Exercise: Attempt to schedule more output
Oracle: No extra generation; incomplete proposal not accepted; active/unresolved resource obligations retained

## BW-G1-012 — Malformed stopped output
Owner: R10 · boundaries: native_cow

Exercise: Validate then decide next permitted step
Oracle: Rejected attempt retained; no regex repair, inferred command or automatic second inference

## BW-G1-013 — Commit before lost acknowledgment
Owner: R10 · boundaries: native_cow, process_restart

Exercise: Reopen client and reconcile exact saved intent
Oracle: Same operation ID/body/revision recovered; no second native generation or branch append

## BW-G1-014 — Stale native revision
Owner: R10 · boundaries: native_cow, process_restart

Exercise: Commit one then attempt other original mutation
Oracle: Second receives conflict; no silent refresh/resend on latest head and no overwriting first result

## BW-G1-015 — Unresolved branch mutation guard
Owner: R28 · boundaries: native_cow, process_restart

Exercise: Request another mutation, fork or rewind on that branch
Oracle: Admission blocked until original operation resolved; unrelated branches can continue within budget

## BW-G1-016 — Uncommitted native interruption
Owner: R10 · boundaries: native_cow, process_restart

Exercise: Reconcile using actual supported status/receipt behavior
Oracle: Native committed/running/unavailable/unknown state preserved accurately; no new ID to hide ambiguity

## BW-G2-001 — Exact bytes and preimages
Owner: R09 · boundaries: filesystem

Exercise: Apply valid patch and conflicting preimage patch
Oracle: Valid postimage matches exact hash; conflicting edit changes nothing and records failure

## BW-G2-002 — Path and link escape
Owner: R09 · boundaries: filesystem

Exercise: Attempt brokered read/write outside grant
Oracle: Canary untouched and unexposed; operations fail for actual resource identity, not only string filtering

## BW-G2-003 — Concurrent path replacement
Owner: R09 · boundaries: filesystem

Exercise: Race link/file identity while performing brokered mutation
Oracle: Operation cannot escape grant; safe refusal or correct anchored write witnessed

## BW-G2-004 — Private control state
Owner: R09 · boundaries: filesystem

Exercise: Attempt file action targeting each protected area
Oracle: Every out-of-scope effect refused with unchanged hashes

## BW-G2-005 — Executable filesystem isolation
Owner: R09 · boundaries: linux_enforcement, process

Exercise: Run a reviewed probe trying absolute/link/proc-mediated access
Oracle: Forbidden reads and writes denied at real OS boundary; allowed candidate access succeeds

## BW-G2-006 — Protect control and shared administration
Owner: R09 · boundaries: linux_enforcement, process

Exercise: Execute under claimed narrow profile
Oracle: All protected effects denied; private authority cannot be reached by inherited handles or same-user escape

## BW-G2-007 — Credential and descriptor isolation
Owner: R09 · boundaries: linux_enforcement, process

Exercise: Start task with filtered env/handles
Oracle: Task cannot obtain fake credential or privileged inherited descriptor; permitted input still works

## BW-G2-008 — Unsupported profile fails closed
Owner: R09 · boundaries: linux_enforcement, process

Exercise: Admit generated-program plan
Oracle: No process launched under weaker profile; explicit unsupported capability recorded without allow-all fallback

## BW-G2-009 — Argv and environment fidelity
Owner: R09 · boundaries: process, linux_enforcement

Exercise: Execute values containing shell metacharacters as arguments
Oracle: No interpolation; observed arguments match and only authorized environment is present

## BW-G2-010 — Real exit and binary streams
Owner: R09 · boundaries: process, linux_enforcement

Exercise: Execute and retain evidence
Oracle: Actual bytes and exit status retained; text rendering does not corrupt raw output or claim task acceptance

## BW-G2-011 — Bounded output and deadline
Owner: R09 · boundaries: process, linux_enforcement

Exercise: Run with limits and observe cleanup
Oracle: Output bounded/truncation explicit; no deadlock or unbounded memory; remaining process state reported

## BW-G2-012 — Threads and descendants
Owner: R09 · boundaries: process, linux_enforcement

Exercise: Stop under qualified profile
Oracle: Descendants handled per actual backend claim; thread count not misreported as workflow branches

## BW-G2-013 — Observation is not unrestricted execution
Owner: R09 · boundaries: process, filesystem

Exercise: Validate then route through legitimate planned effect
Oracle: OBSERVE cannot bypass ACT authority; test run has intent/grant and OBSERVE reads its evidence

## BW-G2-014 — SAVE not first durability
Owner: R09 · boundaries: process, filesystem

Exercise: Interrupt before SAVE
Oracle: Recovery intent remains durable and attributable; absence of SAVE cannot erase side effect

## BW-G2-015 — Trusted verdict over untrusted output
Owner: R09 · boundaries: process, filesystem

Exercise: Evaluate external observed bytes against protected oracle
Oracle: Claims alone fail; trusted evaluator stays separate from candidate code imports/writes

## BW-G2-016 — Fail disposition retained
Owner: R26 · boundaries: process, filesystem

Exercise: Apply VERIFY/CHALLENGE/COMPARE/SELECT and bounded next attempt
Oracle: No publication; failure evidence supplied to subsequent attempt; no weakening of requirement

## BW-G2-017 — New candidate from exact source
Owner: R09 · boundaries: git, filesystem, linux_enforcement

Exercise: Allocate candidate and scratch scope
Oracle: Base identity recorded; user checkout untouched; shared Git admin not writable from candidate process

## BW-G2-018 — Planning source read-only
Owner: R09 · boundaries: git, filesystem, linux_enforcement

Exercise: Inspect source and run permitted observation program
Oracle: Source immutable; only private scratch writable; no project mutation during planning

## BW-G2-019 — Verification source freezing
Owner: R09 · boundaries: git, filesystem, linux_enforcement

Exercise: Attempt concurrent source/test changes while checks execute
Oracle: Mutation blocked or detected and invalidates evidence; output scratch remains usable

## BW-G2-020 — Incomplete baseline actually fails
Owner: R35 · boundaries: process, git, filesystem

Exercise: Execute fixture via product effect boundary and oracle
Oracle: Positive baseline requirements fail; result not mistaken for a solved coding task

## BW-G2-021 — Oracle rejects wrong behavior and object aliasing
Owner: R35 · boundaries: process, git, filesystem

Exercise: Execute each under the same boundary; run the data oracle plus sandboxed input-preservation/fresh-output property probes
Oracle: Each distinguishing mutant rejected; input unchanged and result lists/pairs fresh. serialized typed text output alone is not used to assert Python object identity

## BW-G2-022 — Candidate cannot import authority
Owner: R09 · boundaries: process, git, filesystem

Exercise: Run target CLI in sandbox and verify output externally
Oracle: Verifier receives data only; candidate code never imported into authority process

## BW-G1-017 — Actual textual inputs accompany identities
Owner: R10 · boundaries: native_cow

Exercise: Construct request from authorized artifact bytes
Oracle: Needed content actually supplied; hash alone is not mistaken for remote access

## BW-G1-018 — Same service separate roles
Owner: R10 · boundaries: native_cow

Exercise: Produce design then send accepted design to Builder
Oracle: No unintended role history inheritance; immutable accepted artifact and lineage preserved

## BW-G1-019 — Tool observations do not grant authority
Owner: R10 · boundaries: native_cow

Exercise: Supply through native stopped-turn data input
Oracle: No control-plane authority change; any resulting proposal still subject to frozen contract

## BW-G1-020 — Current physical observations supersede old input
Owner: R10 · boundaries: native_cow

Exercise: Send new evidence and request revised proposal
Oracle: New workspace identity/content made explicit; stale base plan fails preconditions

## BW-G5-001 — Publication success point
Owner: R26 · boundaries: git, filesystem

Exercise: Publish with expected prior ref value
Oracle: Only approved commit becomes target; publication receipt binds before/after and verified source

## BW-G5-002 — Ref divergence and live checkout
Owner: R27 · boundaries: git, filesystem

Exercise: Attempt publication
Oracle: Compare-and-swap conflict or ownership refusal; no forced update of user checkout

## BW-G5-003 — Publication acknowledgment loss
Owner: R26 · boundaries: git, filesystem

Exercise: Reconcile actual target before retry
Oracle: Recovered publication, no duplicate rewrite; successful join only after confirmed publication

## BW-G5-004 — No inherited acceptance after edit
Owner: R26 · boundaries: git, filesystem

Exercise: Attempt publication using old acceptance
Oracle: Publication denied; previous acceptance remains historical but not current

## BW-G6-004 — Live single-task coding outcome
Owner: R14 · boundaries: native_cow, git, process, linux_enforcement

Exercise: Drive the normative workflow through product CLI
Oracle: Actual model-produced valid edit passes protected checks and publishes to owned ref with complete evidence, or trial is recorded as failed

## BW-G6-005 — End-to-end failure remains failure
Owner: R29 · boundaries: native_cow, git, process, linux_enforcement

Exercise: Continue only under explicit budget/contract
Oracle: No fabricated success, test weakening or hidden scripted solution; failed attempt and denominator retained

## BW-G6-006 — Inspect accepted evidence chain
Owner: R29 · boundaries: native_cow, git, process, linux_enforcement

Exercise: Resolve objective through receipts, grant, changes, checks and publication
Oracle: All identities and hashes traceable to exact accepted revision; no missing recovery intent

## BW-G0-013 — Fixed planning input set
Owner: R08 · boundaries: pure

Exercise: Create independent planning branches
Oracle: Both inherit declared same base only; unrelated/sibling events excluded

## BW-G0-014 — Arrival-order independence
Owner: R08 · boundaries: pure

Exercise: Reduce accepted events using explicit causal edges
Oracle: Equivalent visibility and declared selection; append order never leaks sibling content

## BW-G0-015 — Join does not merge numerical states
Owner: R08 · boundaries: pure

Exercise: Admit selected artifact references at join
Oracle: Rejected evidence retained; no invented model snapshot merge or automatic sibling transcript union

## BW-G1-021 — Fork independence with actual native heads
Owner: R10 · boundaries: native_cow

Exercise: Fork and generate both; inspect native histories/heads
Oracle: Parent unchanged and each child contains its own new inputs; answer wording alone not the oracle

## BW-G1-022 — Rewind has correct scope
Owner: R10 · boundaries: native_cow

Exercise: Rewind then continue a distinct new attempt
Oracle: Native state changes as documented, historical local attempt retained and external filesystem unchanged

## BW-G1-023 — Real overlapping planning
Owner: R10 · boundaries: native_cow

Exercise: Hold one active while another progresses and reverse finish order
Oracle: Overlap witnessed from actual operations; causal inputs remain isolated; no sequential imitation

## BW-G1-024 — Two distinct service/store identities
Owner: R10 · boundaries: native_cow, two_services

Exercise: Run same dual-role workflow with different placements
Oracle: Artifacts transfer, not snapshots; both service bindings/receipts retained; two aliases to one store rejected as proof

## BW-G1-025 — Independent model encoding
Owner: R10 · boundaries: native_cow, two_services

Exercise: Establish B context from allowed content then generate
Oracle: No assumption of identical tokenization/state/answers or zero second-service prefill

## BW-G1-026 — Second service failure
Owner: R10 · boundaries: native_cow, two_services

Exercise: Reconcile or block B work
Oracle: A evidence/Git state preserved; no silent reroute/reconstruction or new operation hiding unresolved B

## BW-G4-001 — All scopes allocated before mutation
Owner: R23 · boundaries: git, process, linux_enforcement

Exercise: Delay one allocation while another is ready
Oracle: No child mutation before required allocation barrier; each workspace scope recorded

## BW-G4-002 — Actual concurrent candidate writes
Owner: R23 · boundaries: git, process, linux_enforcement

Exercise: Observe progress and attempt cross-read
Oracle: Distinct files and independent histories; sibling unfinished state inaccessible; overlap witnessed

## BW-G4-003 — Private scratch caches and environment
Owner: R23 · boundaries: git, process, linux_enforcement

Exercise: Write/read through their execution environments
Oracle: No collisions or leakage; authorized read-only base can be shared

## BW-G4-004 — Shared writable resource admission
Owner: R23 · boundaries: process, network, linux_enforcement

Exercise: Admit plans under resource grants
Oracle: Resource partitioned, exclusively serialized or refused; separate worktree not accepted as proof

## BW-G4-005 — Real port ownership
Owner: R23 · boundaries: process, network, linux_enforcement

Exercise: Start listener and retain reservation through handoff
Oracle: No check-then-release fiction; bind failure handled before dependent work; ownership observed

## BW-G4-006 — No leak through shared Git administration
Owner: R23 · boundaries: process, network, linux_enforcement

Exercise: Run under real execution profile
Oracle: Only workspace broker can mutate shared Git administration; unauthorized process denied

## BW-G4-007 — Complementary live coding
Owner: R26 · boundaries: native_cow, git, process, linux_enforcement

Exercise: Verify each, integrate in declared order, run format suite
Oracle: Both required contributions accepted; combined verified commit published with accurate evidence

## BW-G4-008 — Individual pass is not integration pass
Owner: R26 · boundaries: native_cow, git, process, linux_enforcement

Exercise: Integrate and execute protected integration tests
Oracle: Combined result rejected; no publication based solely on child success

## BW-G4-009 — Required child failure
Owner: R23 · boundaries: native_cow, git, process, linux_enforcement

Exercise: Attempt selection and publication
Oracle: Group cannot claim success; all child outcomes retained and successful siblings not silently discarded

## BW-G4-010 — Explicit alternative choice
Owner: R23 · boundaries: git, process

Exercise: Apply predeclared selection contract
Oracle: One chosen result integrated; both not blindly merged; selection evidence recorded

## BW-G4-011 — Alternative tie disposition
Owner: R23 · boundaries: git, process

Exercise: Evaluate tie policy
Oracle: Deterministic declared tie outcome or explicit human selection; no hidden last-finish winner

## BW-G4-012 — Rejected alternative retention
Owner: R23 · boundaries: git, process

Exercise: Dispose only authorized workspace resource
Oracle: Evidence/history preserved; active references and unresolved work not garbage-collected

## BW-G4-013 — Actual merge conflict
Owner: R23 · boundaries: git, process

Exercise: Merge using declared order
Oracle: Real conflict retained as explicit task; no hidden automatic rewrite to force success

## BW-G4-014 — Declared merge order
Owner: R23 · boundaries: git, process

Exercise: Integrate twice in independent fixtures
Oracle: Declared integration order used both times; source/test evidence bound to each exact final commit

## BW-G4-015 — No premature successful join
Owner: R26 · boundaries: git, process

Exercise: Inspect causal ledger before and after confirmation
Oracle: No successful execution join before confirmed required publication; failed group still records outcomes

## BW-G3-005 — Crash after file effect
Owner: R27 · boundaries: process, filesystem, process_restart

Exercise: Reopen and inspect actual bytes
Oracle: Outcome recovered only when evidence sufficient; no duplicate speculative patch

## BW-G3-006 — Unknown nonrepeatable remote effect
Owner: R27 · boundaries: process, filesystem, process_restart

Exercise: Reconcile ambiguous action
Oracle: Remains unresolved and blocks dependency; no automatic second request or fabricated failure

## BW-G3-007 — Explicit compensation
Owner: R27 · boundaries: process, filesystem, process_restart

Exercise: Propose and run compensation
Oracle: New action identity/grant/evidence; original event preserved; no historical deletion or universal rollback claim

## BW-G3-008 — Intent-before-dispatch crash cuts
Owner: R27 · boundaries: filesystem, process_restart

Exercise: Reopen each run independently
Oracle: Only authorized recorded intents eligible for recovery; no inference of non-dispatch from absent receipt

## BW-G3-009 — Artifact/event publication crash cuts
Owner: R26 · boundaries: filesystem, process_restart

Exercise: Scan retained state
Oracle: Orphan object distinguishable from completed event; no missing referenced object accepted

## BW-G3-010 — Partial tail versus committed corruption
Owner: R27 · boundaries: filesystem, process_restart

Exercise: Reopen each fixture
Oracle: Defined tail recovery only; committed corruption/missing evidence blocks progress rather than silent truncation

## BW-G3-011 — Operation cursor restart
Owner: R27 · boundaries: filesystem, process_restart

Exercise: Restart same interpreter
Oracle: Exact original cursor/intents recover; no reconstruction from implicit call stack or repeating prior effects

## BW-G5-005 — Service readiness is observed
Owner: R27 · boundaries: process, network, process_restart

Exercise: Start, check readiness and stop through effect boundary
Oracle: Readiness based on actual endpoint, not process-spawn success; lifecycle/output retained

## BW-G5-006 — PID reuse defense
Owner: R27 · boundaries: process, network, process_restart

Exercise: Attempt reconciliation or termination
Oracle: Unrelated process never signaled/adopted solely by PID; ownership established or blocked

## BW-G5-007 — Controller restart with surviving child
Owner: R27 · boundaries: process, network, process_restart

Exercise: Reopen and inspect startup/ownership evidence
Oracle: Surviving service identified or unresolved; no unearned cleanup/termination claim

## BW-G2-023 — Positive and denied egress
Owner: R09 · boundaries: network, linux_enforcement, process

Exercise: Task attempts both destinations/protocols
Oracle: Allowed communication works; denied connection actually blocked; no third-party targets used

## BW-G2-024 — Inference permission is not task permission
Owner: R09 · boundaries: network, linux_enforcement, process

Exercise: Candidate attempts same endpoint/credential
Oracle: Candidate receives no inherited permission or key; BW native operation remains functional

## BW-G2-025 — IPC framing and binary data
Owner: R09 · boundaries: network, linux_enforcement, process

Exercise: Exchange allowed binary frames and exceed limits
Oracle: Correct framing/bytes and bounded rejection; handles owned and cleaned; no text-only corruption

## BW-G2-026 — Listener and external write grants
Owner: R09 · boundaries: network, linux_enforcement, process

Exercise: Admit under default local fixture grant
Oracle: Dispatch denied before effect; broader authority only via separate explicit grant

## BW-G5-008 — Parent budget conservation
Owner: R28 · boundaries: native_cow, process

Exercise: Exhaust native/action/disk admission across branches
Oracle: Sum of grants cannot create new allowance; no retry or child gets free independent budget

## BW-G5-009 — Shared endpoint capacity
Owner: R28 · boundaries: native_cow, process

Exercise: Schedule concurrent work above bound
Oracle: One service capacity bound enforced; aliases/roles do not multiply allowance

## BW-G5-010 — Cancelled remote work remains reserved
Owner: R28 · boundaries: native_cow, process

Exercise: terminal disposition and schedule next work
Oracle: Report unresolved remote work; no capacity released as if termination confirmed

## BW-G5-011 — terminal disposition descendant outcomes
Owner: R27 · boundaries: native_cow, process

Exercise: Escalate only within authorized profile and observe
Oracle: Actual stopped/surviving/unresolved processes distinguished; stop request not falsely labeled complete

## BW-G5-012 — Rewind never undoes external work
Owner: R27 · boundaries: native_cow, git, process

Exercise: Rewind context to earlier snapshot
Oracle: File/counter unchanged; interface explicitly separates model position from real resources

## BW-G5-013 — New attempt binds truthful base
Owner: R27 · boundaries: native_cow, git, process

Exercise: Start another attempt from historical point
Oracle: Current observations supplied or new appropriate context established; stale preconditions cannot authorize work

## BW-G5-014 — Unavailable numerical checkpoint
Owner: R28 · boundaries: native_cow, git, process

Exercise: Attempt recovery/continuation
Oracle: Native limitation visible; any authorized textual reconstruction has new lineage and budget, not a restoration claim

## BW-G5-015 — Verification bound to exact revision
Owner: R27 · boundaries: git, process, linux_enforcement

Exercise: Attempt edit during/after verification
Oracle: Checks identify immutable revision; changed source loses current acceptance; historical success remains

## BW-G5-016 — Protected requirements cannot weaken
Owner: R27 · boundaries: git, process, linux_enforcement

Exercise: PLAN and execute under task grant
Oracle: Protected requirement change rejected unless separate owner-authorized contract revision exists

## BW-G5-017 — Combined evidence trace completeness
Owner: R26 · boundaries: git, process, linux_enforcement

Exercise: Independently traverse all referenced artifacts
Oracle: Contract, inputs, plan/grant, effect outcomes, checks and publication recoverable by exact identities

## BW-G6-007 — Inspection is locally read-only
Owner: R29 · boundaries: process, filesystem

Exercise: Execute show and tree while watching file/network effects
Oracle: No inference, hidden remote refresh or persistent mutation; projections readable from retained state

## BW-G6-008 — new dispatches no task effects
Owner: R26 · boundaries: process, filesystem

Exercise: Execute new
Oracle: Only local run records created; no model generation, candidate program or publication

## BW-G6-009 — step and run share transitions
Owner: R29 · boundaries: process, filesystem

Exercise: Advance via repeated step and via run
Oracle: Same semantic events/outcomes; no separate fast-path controller or unbounded hidden loop

## BW-G6-010 — verify and reconcile own effects honestly
Owner: R29 · boundaries: process, filesystem

Exercise: Invoke respective commands
Oracle: Effects use normal grants/intents; reconcile not misadvertised universally read-only

## BW-G6-011 — Status distinctions visible
Owner: R29 · boundaries: process, filesystem

Exercise: Display text/tree
Oracle: States not collapsed to done; task/context/workspace identities shown distinctly

## BW-G6-012 — Redaction does not falsify output
Owner: R29 · boundaries: process, filesystem

Exercise: Generate report/view
Oracle: Truncation/redaction labeled with provenance; no credentials leak; raw evidence remains private

## BW-G6-013 — No second canonical transcript
Owner: R29 · boundaries: process, filesystem

Exercise: Reopen display and resume qualified run
Oracle: Authoritative native/ledger state intact; display cache never drives transcript replay or independent transitions

## BW-G6-014 — Prefix reuse measurement
Owner: R29 · boundaries: native_cow, gpu_telemetry

Exercise: Fork/resume controlled native context and retain counters
Oracle: Claimed reuse follows measured native work, not only lower latency; absent counters cannot pass this measurement

## BW-G6-015 — Per-trial performance denominator
Owner: R29 · boundaries: native_cow, gpu_telemetry

Exercise: Record time/tokens/memory where actually observable
Oracle: Warmup separate, failed trials retained, unavailable counters null; no invented throughput or numerical equivalence

## BW-G6-016 — Functional versus numerical claim
Owner: R29 · boundaries: native_cow, gpu_telemetry

Exercise: Produce capability report
Oracle: Functional success not relabeled numerical equivalence; GPU/state claims restricted to actual evidence

## BW-G6-017 — Owned native server restart
Owner: R29 · boundaries: process_restart, native_cow

Exercise: Commit operation, restart owned coordinator, recover original intent
Oracle: Durable receipt behavior observed across actual restart; no process-local UNKNOWN interpreted as noncommitment

## BW-G6-018 — Service identity after replacement
Owner: R29 · boundaries: process_restart, native_cow

Exercise: Reconnect old context reference
Oracle: Reject substitution or require explicit new lineage; same URL not treated as restored context

## BW-G6-019 — Platform and durability scope
Owner: R31 · boundaries: process_restart, native_cow

Exercise: Emit release qualification report
Oracle: No Windows/macOS or power-loss PASS inferred; missing required profile cases explicitly blocked/unqualified

## BW-G6-020 — No destructive durability test by default
Owner: R31 · boundaries: process_restart, native_cow

Exercise: Evaluate qualification dispatch
Oracle: No power-cycle/reboot attempted; inability to run this qualification remains visible rather than fabricated

## BW-G6-021 — Real campaign not model script
Owner: R35 · boundaries: native_cow, git, process, linux_enforcement

Exercise: Execute single, complementary and alternative workflows
Oracle: Actual committed model outputs used; synthetic/fault fixtures labeled separately; live outcomes and denominators retained

## BW-G6-022 — Blocked native scope remains blocked
Owner: R29 · boundaries: native_cow, git, process, linux_enforcement

Exercise: Run campaign/report generation
Oracle: Supported milestones reported; missing cases blocked/not_run rather than counted PASS or silently excluded

## BW-G6-023 — Final resource accounting
Owner: R29 · boundaries: native_cow, git, process, linux_enforcement

Exercise: Audit ownership and cleanup
Oracle: Only owned known-safe resources removed; remaining contexts/processes/ports/reservations listed for recovery

## BW-G6-024 — Clean source reproducibility
Owner: R29 · boundaries: git, filesystem, process

Exercise: Follow documented install/test/campaign commands
Oracle: Same implementation/tests runnable without private undocumented edits; no global environment mutation

## BW-G6-025 — Acceptance inventory completeness
Owner: R29 · boundaries: git, filesystem, process

Exercise: Audit all required IDs and evidence
Oracle: No unknown/duplicate/missing cases, no empty PASS evidence; skipped cases not converted into passes

## BW-G6-026 — Usable final deliverable
Owner: R14 · boundaries: git, filesystem, process

Exercise: Follow operator guide from new run
Oracle: Owner can inspect, step, run, verify, reconcile and stop with exact command documentation; limits honestly stated

## BW-G0-016 — Lossless typed round trip
Owner: R02 · boundaries: pure

Exercise: Persist, reload and bind values to declared result slots
Oracle: Types and exact values survive; missing remains distinguishable from null; no boolean-as-integer or string coercion

## BW-G0-017 — Raw bytes remain bytes
Owner: R08 · boundaries: pure

Exercise: Retain binary outputs and render bounded textual observations
Oracle: Exact bytes/digests retained; rendering loss and truncation explicit; no accidental text decoding replaces binary truth

## BW-G0-018 — Reject wrong result kind
Owner: R05 · boundaries: pure

Exercise: Validate and attempt to bind the result
Oracle: Wrong type fails before slot binding; no parent resume or task acceptance

## BW-G0-019 — Reject duplicate fields and unknown variants
Owner: R02 · boundaries: pure

Exercise: Decode complete committed output through the canonical type contract
Oracle: All rejected explicitly; no last-key-wins, guessed variant, or implicit schema migration

## BW-G0-020 — Same shape does not mean same authority
Owner: R08 · boundaries: pure

Exercise: Attempt protected acceptance using each value
Oracle: Provenance remains distinct; model claim cannot stand in for observed evidence

## BW-G0-021 — Immutable argument and result bindings
Owner: R05 · boundaries: pure

Exercise: Attempt mutation of a child local value then return a new value
Oracle: Parent/sibling bindings unchanged; only admitted typed return edges create new bindings

## BW-G0-022 — Control handles cannot be forged
Owner: R08 · boundaries: pure

Exercise: Attempt use outside the call input and capability scope
Oracle: Shape-valid text cannot create authority, access a hidden artifact, or choose the return destination

## BW-G0-023 — Nested typed call and return
Owner: R05 · boundaries: pure

Exercise: Call A to B to C; return C then B
Oracle: Exact immediate continuation resumes with each declared type; not the current UI-selected node

## BW-G0-024 — Preserve parent locals across child call
Owner: R05 · boundaries: pure

Exercise: Run child then resume parent
Oracle: Original locals persist; declared return slot alone changes; PC advances to exact admitted location

## BW-G0-025 — Only one eligible result delivery
Owner: R05 · boundaries: pure

Exercise: Apply return delivery repeatedly
Oracle: One logical slot binding and one eligible parent resumption; replay is recognized without duplicate dispatch

## BW-G0-026 — Conflicting duplicate return is rejected
Owner: R08 · boundaries: pure

Exercise: Attempt second delivery
Oracle: Recorded conflict; original value retained; no overwrite

## BW-G0-027 — Wrong parent or wait slot is rejected
Owner: R05 · boundaries: pure

Exercise: Send one child result to the other wait or slot
Oracle: Ownership and expected child identity reject misrouting despite matching type

## BW-G0-028 — Old continuation epoch is rejected
Owner: R05 · boundaries: pure

Exercise: Deliver a late result carrying the old epoch
Oracle: Old result stays attributable in history; new wait remains unsatisfied

## BW-G0-029 — Retire active frame without moving history
Owner: R05 · boundaries: pure

Exercise: Return then rebuild active and completed views
Oracle: Leaf absent from active frontier; original node/edges/value retained once in history and referenced from views

## BW-G0-030 — Partial model output is not function return
Owner: R05 · boundaries: pure

Exercise: Attempt parent delivery before expected turn boundary
Oracle: Parent remains waiting; no premature typed return

## BW-G0-031 — Frame states cannot contradict
Owner: R08 · boundaries: pure

Exercise: Construct closed-with-unresolved-owned-operation and simultaneously-ready-and-waiting variants
Oracle: Invalid states rejected; no flags permitting dispatch after close

## BW-G0-032 — Loop iterations retain distinct calls
Owner: R08 · boundaries: pure

Exercise: Complete both with different values
Oracle: Distinct invocation, attempt/iteration and continuation identities; prior result not overwritten

## BW-G0-033 — Handler call obeys ordinary return rules
Owner: R28 · boundaries: pure

Exercise: Handle error with another bounded procedure
Oracle: Handler has recorded inputs/grants/budget and return edge; cannot erase error or broaden authority

## BW-G3-012 — Crash between child result and parent resume
Owner: R27 · boundaries: filesystem, process

Exercise: Crash before resumption, reopen, and continue
Oracle: One result delivery; correct restored PC/locals; no rerun of tool or model generation

## BW-G3-013 — Admission and wait registration are indivisible
Owner: R27 · boundaries: filesystem, process

Exercise: Restart and inspect ledger and dispatch log
Oracle: Either no admitted child or one child with its owning return/wait record; never an orphan dispatch

## BW-G3-014 — Return and slot binding have one success point
Owner: R05 · boundaries: filesystem, process

Exercise: Restart and replay durable ledger
Oracle: Closed child cannot lose its return; parent cannot accept a nonexistent result; no double delivery

## BW-G3-015 — Rebuild active frontier and history projections
Owner: R05 · boundaries: filesystem, process

Exercise: Reopen from immutable definitions, ledger and artifacts
Oracle: Same frames, slots, typed values, stream commitments and completed history; no regeneration

## BW-G3-016 — Uncertain tool keeps ownership after crash
Owner: R28 · boundaries: filesystem, process

Exercise: Restart and attempt to close parent or run
Oracle: Dependent continuation remains waiting or explicit ownership transfer occurs; uncertainty and capacity not discarded

## BW-G3-017 — Closed parent rejects a late result safely
Owner: R27 · boundaries: filesystem, process

Exercise: Retain late observation and process delivery
Oracle: History records original provenance; closed/superseded continuation never resumes; remaining resource duties reconciled

## BW-G0-034 — Single source of generation type contracts
Owner: R02 · boundaries: pure

Exercise: Compare runtime validator, serialized type identity and generated output description
Oracle: Same version/hash and accepted shapes; no independently edited conflicting schemas

## BW-G0-035 — Missing template input fails before inference
Owner: R13 · boundaries: pure

Exercise: Omit that slot and admit generation
Oracle: Explicit validation error before CowClient dispatch or budget consumption for inference

## BW-G0-036 — Template content is not recursively interpreted
Owner: R13 · boundaries: pure

Exercise: Render the exact pinned template once
Oracle: User/tool data retained literally; no recursive interpolation, code evaluation or phantom required slots

## BW-G0-037 — Template version is pinned for retries
Owner: R13 · boundaries: pure

Exercise: Recover the original operation and finish; then make a new invocation
Oracle: Original bytes/version persist through recovery; new invocation can use v2 with distinct definition identity

## BW-G0-038 — Unknown template fields do not become instructions
Owner: R13 · boundaries: pure

Exercise: Attempt generator admission
Oracle: Reject contract mismatch; do not silently append unknown fields to the model prompt

## BW-G0-039 — Generation definition grants no tool authority
Owner: R02 · boundaries: pure

Exercise: Attempt to turn its output into a tool dispatch
Oracle: Declared output type/authority rejects effect; text content cannot change the generator procedure

## BW-G1-027 — Native headline generation is an ordinary call
Owner: R13 · boundaries: native_cow, filesystem

Exercise: Run headline generation through EXPAND/CONTINUE and return Headline
Oracle: Retained template/input/native receipts and typed output; no hardcoded canned headline

## BW-G1-028 — Native status narration is source-bound
Owner: R13 · boundaries: native_cow, filesystem

Exercise: Generate a StatusNote on the real service
Oracle: Note references exact frontier; factual status unchanged; success prose cannot mark test passed

## BW-G1-029 — Native evidence summary retains source identities
Owner: R13 · boundaries: native_cow, filesystem

Exercise: Generate and validate an EvidenceSummary
Oracle: Source refs known/in-scope; unresolved inputs retained in structured fields; raw observations not replaced

## BW-G1-030 — Native final response is evidence-bound
Owner: R10 · boundaries: native_cow, filesystem

Exercise: Generate FinalResponse via the same EXPAND/CONTINUE driver
Oracle: Response references accepted and failed evidence separately; no narrative-only acceptance

## BW-G1-031 — Auxiliary context cannot pollute parent
Owner: R10 · boundaries: native_cow, filesystem

Exercise: Generate headline/summary on an isolated child and resume Builder
Oracle: Native parent history/head has no auxiliary prompt; only an explicitly selected result may be supplied

## BW-G1-032 — In-flight parent cannot be forked accidentally
Owner: R10 · boundaries: native_cow, filesystem

Exercise: Schedule an auxiliary request whose lineage demands that source
Oracle: Wait or explicitly fail source availability; never fork mutable in-flight head or silently reconstruct another lineage

## BW-G1-033 — Same server same model distinct invocation roles
Owner: R10 · boundaries: native_cow, filesystem

Exercise: Run nested design/tool/title/summary sequence
Oracle: Distinct scoped contexts/identities where required; single server limits and same continuation semantics

## BW-G6-027 — Factual status does not depend on LLM wording
Owner: R13 · boundaries: filesystem

Exercise: Render show/status/tree and inspect requests
Oracle: Truthful deterministic status; zero inference; no fake generated note

## BW-G6-028 — Stale status completion stays historical
Owner: R29 · boundaries: filesystem

Exercise: Consume both valid outputs
Oracle: E1 cannot overwrite E2 current annotation; both retain exact sources and timestamps

## BW-G6-029 — Delayed title cannot override a user rename
Owner: R29 · boundaries: filesystem

Exercise: Deliver its result after the user edit
Oracle: Generated result retained as historical/suggestion; explicit user revision wins

## BW-G6-030 — Presentation failure cannot alter task truth
Owner: R28 · boundaries: filesystem

Exercise: Settle annotation error and display outcome
Oracle: Code acceptance unchanged; presentation failure shown as its own typed error and budget accounted

## BW-G6-031 — Generated notes do not trigger infinite notes
Owner: R29 · boundaries: filesystem

Exercise: Record generation start/deltas/result and refresh display repeatedly
Oracle: No recursive generation from its own lifecycle or view refresh; one admitted job per declared trigger identity

## BW-G6-032 — Summary references are checked not trusted
Owner: R13 · boundaries: filesystem

Exercise: Validate its structured output
Oracle: Reject inadmissible source binding before adoption; raw summary remains untrusted evidence

## BW-G6-033 — Condensed context does not replace runtime state
Owner: R05 · boundaries: filesystem

Exercise: Summarize and explicitly initialize/select a condensed model lineage
Oracle: Exact slots/types/grants/resources/native uncertainty remain outside prose; original evidence and history preserved

## BW-G6-034 — Raw streams and summaries remain linked
Owner: R13 · boundaries: filesystem

Exercise: Inspect derived and raw views
Oracle: Explicit truncation/redaction/omissions and source digests; summary not advertised as full output

## BW-G1-034 — Reasoning capability is discovered not assumed
Owner: R10 · boundaries: native_cow

Exercise: Qualify raw reasoning, summary and control support separately
Oracle: Each supported channel has evidence; unavailable features labeled unavailable, not an invented PASS

## BW-G1-035 — Reasoning and final channels cannot substitute
Owner: R10 · boundaries: native_cow

Exercise: Stream it before a real committed final value
Oracle: Reasoning retained under correct channel; no parser dispatches it as a tool request

## BW-G1-036 — Generated analysis is not claimed native reasoning
Owner: R10 · boundaries: native_cow

Exercise: Invoke ReasoningNote through an ordinary template
Oracle: Output labeled generated analysis with native receipt, not recovered hidden reasoning

## BW-G1-037 — Reasoning controls must be actually accepted
Owner: R10 · boundaries: native_cow

Exercise: Bind and run generator settings
Oracle: Recorded requested/effective values; unsupported option rejected or unavailable, never silently faked

## BW-G1-038 — Channel framing is source-pinned
Owner: R10 · boundaries: native_cow

Exercise: Decode using qualified profile boundary
Oracle: No guessed regex strips or reclassifies task text; unsupported framing explicit

## BW-G1-039 — Committed partial does not complete return
Owner: R10 · boundaries: native_cow

Exercise: Continue while preserving channel/item identity
Oracle: One logical output assembled only at expected stop; each operation receipt separately retained

## BW-G1-040 — Reconnection cannot duplicate streamed values
Owner: R10 · boundaries: native_cow

Exercise: Recover original operation and render/reassemble
Oracle: Exact canonical committed bytes and one ordered segment history; no duplicate append or lossy UTF-8

## BW-G1-041 — Native thinking absent does not erase ordinary tool support
Owner: R10 · boundaries: native_cow

Exercise: Run typed tool-request/result loop and visible generated analysis
Oracle: Ordinary loop can pass its actual tests; raw reasoning remains unavailable, not silently emulated

## BW-G1-042 — Typed committed tool yield and return
Owner: R10 · boundaries: native_cow, process, filesystem

Exercise: Validate PLAN/grant, invoke tool child, return observation and append it to owner context
Oracle: One correlated request/plan/grant/execution/result/delivery chain; no invisible adapter tool loop

## BW-G1-043 — Wrong-call tool result never reaches model
Owner: R10 · boundaries: native_cow, process, filesystem

Exercise: Swap call IDs or owner invocation during delivery
Oracle: Wrong owner/correlation rejected before context append; correct wait remains

## BW-G1-044 — Tool denial is a typed result
Owner: R10 · boundaries: native_cow, process, filesystem

Exercise: Deny then supply declared error observation to the owner
Oracle: No effect dispatch; denial retained; model receives actual denial, not fake success or expanded grant

## BW-G1-045 — Several tool rounds use the same kernel
Owner: R10 · boundaries: native_cow, process, filesystem

Exercise: Drive all rounds through step/run
Oracle: Each request has distinct child/operation identity and one recorded return; no second worker-owned loop

## BW-G1-046 — Tool result preserves false empty and failure values
Owner: R10 · boundaries: native_cow, process, filesystem

Exercise: Return values to typed bindings and serialize supported observations to COW
Oracle: No truthiness-as-missing bug; nonzero exit not converted into accepted task or lost observation

## BW-G2-027 — Observed process outcome is distinct from accepted task
Owner: R09 · boundaries: process, filesystem

Exercise: Return ProcessResult then VERIFY/CHALLENGE/COMPARE/SELECT required output
Oracle: Process result is retained correctly; task acceptance fails independently

## BW-G2-028 — Tool output cannot modify continuation or grant
Owner: R09 · boundaries: process, filesystem

Exercise: Decode and return output through the registered tool schema
Oracle: Ordinary output data only; protected control bindings unchanged

## BW-G2-029 — Service handles retain lifecycle ownership on return
Owner: R09 · boundaries: process, filesystem

Exercise: Return its logical service result and later finish parent
Oracle: Service has explicit owning scope or recorded transfer; no orphan process from retiring the child

## BW-G4-016 — Parallel children fill named return slots
Owner: R05 · boundaries: pure

Exercise: Join their typed values
Oracle: Same declared mapping/order; no global stack pop or last-result-wins

## BW-G4-017 — Parallel valid second result survives first binding
Owner: R05 · boundaries: pure

Exercise: Deliver the second legitimate result
Oracle: Second slot accepts its declared child; naive global revision check cannot reject it

## BW-G4-018 — Join can resume only once
Owner: R23 · boundaries: pure

Exercise: Resume the parent
Oracle: Exactly one logical join/resumption; duplicate is idempotent; retained child history unchanged

## BW-G5-018 — Cancellation unwinds without losing uncertain children
Owner: R05 · boundaries: process, filesystem

Exercise: Cancel scope and inspect resources/late returns
Oracle: No new effects; settled children retire; uncertain work stays owned and budgeted; no false closed state

## BW-G5-019 — Annotation scope is owned without blocking code dependency
Owner: R27 · boundaries: process, filesystem

Exercise: Finish main body then request run termination
Oracle: Main dependency can complete independently; run accounts for title cancellation/result before close or transfers explicitly

## BW-G5-020 — Shared budgets include helper generations
Owner: R28 · boundaries: process, filesystem

Exercise: Consume a small total budget concurrently
Oracle: No hidden free helper calls or reset child budgets; reserved unresolved capacity remains accounted

## BW-G6-035 — User question returns to the intended waiting frame
Owner: R05 · boundaries: filesystem

Exercise: Reply to one via interface and restart
Oracle: Only matching slot filled once; question/answer recorded; other wait persists

## BW-G6-036 — Stale human reply is not injected after retry
Owner: R14 · boundaries: filesystem

Exercise: Submit the old reply
Oracle: Retain or reject as stale under explicit policy; no delivery to new active task

## BW-G6-037 — Steering respects unresolved native mutation
Owner: R29 · boundaries: filesystem

Exercise: Queue it then reconcile and admit at safe boundary
Oracle: Typed queued input retained; no unsafe append-user or silent input loss

## BW-G6-038 — Complete real nested session includes generators
Owner: R05 · boundaries: native_cow, process, filesystem, git

Exercise: Run headline/design/tool/fix/retest/summary/final through product
Oracle: All required calls and typed returns observable; actual correct candidate; no canned generator or runtime bypass

## BW-G6-039 — Native parent recovery after durable child return
Owner: R29 · boundaries: native_cow, process, filesystem, git

Exercise: Interrupt BW and restart through production CLI
Oracle: Resume exact continuation once; no repeated effect or child generation; parent receives correct typed evidence

## BW-G6-040 — Live summary reveals preserved failed attempt
Owner: R13 · boundaries: native_cow, process, filesystem, git

Exercise: Generate final summary and inspect source links
Oracle: Failure and unresolved data retained, distinct from accepted revision; required source fields verified independently

## BW-G6-041 — Two services preserve the same typed return semantics
Owner: R05 · boundaries: native_cow, process, filesystem, git

Exercise: Execute the same nested calls and accepted artifact handoff
Oracle: Same types, return ownership and authority semantics; no cross-service context ID substitution

## BW-G6-042 — No product-completion claim from missing features
Owner: R29 · boundaries: native_cow, process, filesystem, git

Exercise: Evaluate release feature matrix
Oracle: Release incomplete; missing native channels separately identified rather than hiding unimplemented required runtime features

## BW3-LANG-001 — No model JSON dependency
Owner: R02 · boundaries: parser, type_boundary

Exercise: Generate a complete non-JSON BW decision through the actual model path
Oracle: Typed value admitted without JSON mode, schema conversion or tool JSON envelope

## BW3-LANG-002 — Reject legacy executable aliases
Owner: R02 · boundaries: parser, type_boundary

Exercise: Submit ASK DO LOOK CHECK STOP as program operations
Oracle: Fail explicitly; no guessed compatibility elaboration at runtime

## BW3-LANG-003 — Literal instruction containment
Owner: R02 · boundaries: parser, type_boundary

Exercise: Return TEXT containing ACT COMMIT END and shell-like content
Oracle: Literal data survives unchanged; no nested parsing or dispatch

## BW3-LANG-004 — UTF-8 and LF contract
Owner: R02 · boundaries: parser, type_boundary

Exercise: Round-trip Unicode including U+2028, a line beginning with a pipe and empty text
Oracle: Declared LF rule and Unicode bytes preserved without splitlines corruption

## BW3-LANG-005 — Duplicate and unknown fields
Owner: R02 · boundaries: parser, type_boundary

Exercise: Submit duplicate plan fields and unregistered arguments
Oracle: Reject before inference/effect dispatch, without last-field-wins

## BW3-LANG-006 — Bounded parse complexity
Owner: R02 · boundaries: parser, type_boundary

Exercise: Submit excessive depth, length, node count and unclosed blocks
Oracle: Bounded explicit errors without auto-closing or side effects

## BW3-LANG-007 — Single source for shape and grammar
Owner: R02 · boundaries: parser, type_boundary

Exercise: Change an operation field definition and regenerate grammar/validator
Oracle: Both change together; stale definition/grammar identities rejected

## BW3-LANG-008 — Handle is not authority
Owner: R02 · boundaries: parser, type_boundary

Exercise: Nominate a valid-looking path or artifact digest outside the visible scope
Oracle: No read or write is granted by syntax alone

## BW3-LANG-009 — Trusted return destination
Owner: R02 · boundaries: parser, type_boundary

Exercise: Model proposes a parent slot or invocation identity it does not own
Oracle: Host-owned wait identity remains authoritative

## BW3-LANG-010 — Unknown variant and type version
Owner: R02 · boundaries: parser, type_boundary

Exercise: Return an unsupported typed result variant/version
Oracle: Reject rather than coerce or infer a legacy schema

## BW3-LANG-011 — Complete stopped value required
Owner: R02 · boundaries: parser, type_boundary

Exercise: Stream a valid prefix and stop malformed or remain active
Oracle: No typed return or ACT before full committed admitted boundary

## BW3-LANG-012 — Canonical program identity
Owner: R02 · boundaries: parser, type_boundary

Exercise: Reparse and render a program under the pinned whitespace rule
Oracle: Stable typed AST/digest; undocumented text normalization rejected

## BW3-PLAN-001 — Unrelated sibling event stays irrelevant
Owner: R08 · boundaries: interpreter, policy, resource_boundary

Exercise: Advance A while B depends only on unchanged source and B-local state
Oracle: B remains fresh; no comparison to global latest ledger revision

## BW3-PLAN-002 — Relevant file mutation stales plan
Owner: R08 · boundaries: interpreter, policy, resource_boundary

Exercise: Change a file in the plan dependency closure
Oracle: Dispatch is rejected until an explicitly new plan and grant

## BW3-PLAN-003 — Profile change changes identity
Owner: R08 · boundaries: interpreter, policy, resource_boundary

Exercise: Change stage order or an accepted sampler parameter
Oracle: Plan/profile digest changes and old grant cannot authorize it

## BW3-PLAN-004 — Grammar change changes identity
Owner: R08 · boundaries: interpreter, policy, resource_boundary

Exercise: Change allowed handles or grammar epoch
Oracle: Existing plan is not relabeled as using the new grammar

## BW3-PLAN-005 — Unknown future state is not frozen
Owner: R08 · boundaries: interpreter, policy, resource_boundary

Exercise: Author a flow whose second action needs the first result
Oracle: Second concrete plan waits for the actual result rather than guessing its version

## BW3-PLAN-006 — Checked mutation boundary
Owner: R08 · boundaries: interpreter, policy, resource_boundary

Exercise: Race a preimage change between inspection and dispatch
Oracle: Real compare-and-swap/lock rejects stale mutation; no check-then-write gap

## BW3-PLAN-007 — Expired grant or lease
Owner: R08 · boundaries: interpreter, policy, resource_boundary

Exercise: Expire authority after model output but before dispatch
Oracle: Grammar-valid nomination cannot bypass the live recheck

## BW3-PLAN-008 — Service identity mismatch
Owner: R08 · boundaries: interpreter, policy, resource_boundary

Exercise: Reuse a URL with a different store/model/tokenizer
Oracle: Old context binding fails before dispatch

## BW3-PLAN-009 — Dependency completeness
Owner: R08 · boundaries: interpreter, policy, resource_boundary

Exercise: Change executable, environment or protected test input without changing candidate text
Oracle: Acceptance and plan freshness respond to the actual dependency closure

## BW3-PLAN-010 — Canonical plan hashing
Owner: R08 · boundaries: interpreter, policy, resource_boundary

Exercise: Construct semantically identical bindings in different map insertion order
Oracle: Same canonical plan identity without lossy value conversion

## BW3-PLAN-011 — Frozen bytes are immutable
Owner: R08 · boundaries: interpreter, policy, resource_boundary

Exercise: Edit a template or patch after admission
Oracle: Old plan retains original bytes; new version needs new identity

## BW3-PLAN-012 — Observation is not program execution
Owner: R08 · boundaries: interpreter, policy, resource_boundary

Exercise: Nominate a cache-writing test executable as OBSERVE
Oracle: Requires planned effect capability; no read-label bypass

## BW3-GRAM-001 — Grammar-first actual ordering
Owner: R15 · boundaries: native_grammar, tokenizer, native_fork

Exercise: Use logits whose global top token is forbidden and Min-P would discard legal tokens before masking
Oracle: Legal set is established before the certified soft sampling law

## BW3-GRAM-002 — Independent sibling progress
Owner: R15 · boundaries: native_grammar, tokenizer, native_fork

Exercise: Fork at one committed partial record; advance A to END while B stays inside a field
Oracle: B retains its own valid next-token set and incomplete state

## BW3-GRAM-003 — Reject probe rollback
Owner: R15 · boundaries: native_grammar, tokenizer, native_fork

Exercise: Probe illegal tokens repeatedly before selecting a legal one
Oracle: Committed matcher prefix/state remains unchanged by rejected probes

## BW3-GRAM-004 — Multi-character token correctness
Owner: R15 · boundaries: native_grammar, tokenizer, native_fork

Exercise: Use a token piece spanning delimiter, newline and part of the next field
Oracle: All its bytes are checked against the same grammar transition

## BW3-GRAM-005 — Partial UTF-8 fork
Owner: R15 · boundaries: native_grammar, tokenizer, native_fork

Exercise: Checkpoint and fork at a native-supported partial Unicode token boundary
Oracle: Each child resumes the exact matcher state or capability is explicitly unavailable

## BW3-GRAM-006 — EOS only at valid boundary
Owner: R15 · boundaries: native_grammar, tokenizer, native_fork

Exercise: Propose end-of-generation inside and after a complete record
Oracle: EOS respects the qualified grammar and turn contract

## BW3-GRAM-007 — Continue does not reset grammar
Owner: R15 · boundaries: native_grammar, tokenizer, native_fork

Exercise: Split one active output across multiple committed token-limited requests
Oracle: Later chunks continue the existing matcher, not a root matcher

## BW3-GRAM-008 — New contract starts at permitted boundary
Owner: R15 · boundaries: native_grammar, tokenizer, native_fork

Exercise: Request a different output grammar during an active turn
Oracle: Reject or create an explicit qualified new lineage; no live grammar swap

## BW3-GRAM-009 — Grammar snapshot source freshness
Owner: R15 · boundaries: native_grammar, tokenizer, native_fork

Exercise: Freeze allowed handles, then change a referenced plan before completion
Oracle: Grammar completion still undergoes semantic freshness validation

## BW3-GRAM-010 — Empty hard legal set
Owner: R15 · boundaries: native_grammar, tokenizer, native_fork

Exercise: Construct an incompatible grammar/tokenizer/stop configuration
Oracle: Explicit decode failure; no unconstrained fallback

## BW3-GRAM-011 — Singleton legality and sampler safety
Owner: R15 · boundaries: native_grammar, tokenizer, native_fork

Exercise: Enable all qualified soft stages with only one legal token
Oracle: No stage removes the final admissible candidate or invents another

## BW3-GRAM-012 — Prompt-prefilled grammar progress
Owner: R15 · boundaries: native_grammar, tokenizer, native_fork

Exercise: Use a native template that already includes part of the output record
Oracle: Qualified prefill treatment prevents duplicate/missing prefix consumption

## BW3-GRAM-013 — Reasoning and data cannot execute
Owner: R15 · boundaries: native_grammar, tokenizer, native_fork

Exercise: Expose reasoning text or a literal block that looks like a control instruction
Oracle: Only the admitted output channel/contract can produce a control value

## BW3-GRAM-014 — Immutable grammar compilation sharing
Owner: R15 · boundaries: native_grammar, tokenizer, native_fork

Exercise: Compile/fork grammars concurrently and interleave branch matching
Oracle: Shared tables remain immutable; live matcher state is not shared

## BW3-SAMPLE-001 — Exactly one terminal selector
Owner: R16 · boundaries: native_sampler, checkpoint, numerical_oracle

Exercise: Configure dist with Mirostat or Adaptive-P with greedy
Oracle: Reject invalid chain before generation

## BW3-SAMPLE-002 — Temperature alternatives
Owner: R16 · boundaries: native_sampler, checkpoint, numerical_oracle

Exercise: Enable static and dynamic temperature in an undeclared double-stage profile
Oracle: Reject rather than quietly double-transform

## BW3-SAMPLE-003 — Exact clone versus diversity
Owner: R16 · boundaries: native_sampler, checkpoint, numerical_oracle

Exercise: Clone identical logits, profile and full RNG state then sample siblings
Oracle: Replay equality is tested; it is not claimed as diversified exploration

## BW3-SAMPLE-004 — Stable exploration seed split
Owner: R16 · boundaries: native_sampler, checkpoint, numerical_oracle

Exercise: Launch the same named children in reversed order
Oracle: Per-child/component streams match across launch orders

## BW3-SAMPLE-005 — Component-local randomness
Owner: R16 · boundaries: native_sampler, checkpoint, numerical_oracle

Exercise: Enable XTC on A or make extra diagnostic draws in A
Oracle: B selector RNG sequence remains unchanged

## BW3-SAMPLE-006 — Dry history independence
Owner: R16 · boundaries: native_sampler, checkpoint, numerical_oracle

Exercise: Generate repeated tokens on A after the fork
Oracle: B DRY penalty/history remains its own

## BW3-SAMPLE-007 — Mirostat feedback independence
Owner: R16 · boundaries: native_sampler, checkpoint, numerical_oracle

Exercise: Change A feedback state after accepted tokens
Oracle: B control state and law remain unchanged

## BW3-SAMPLE-008 — Adaptive-P feedback independence
Owner: R16 · boundaries: native_sampler, checkpoint, numerical_oracle

Exercise: Change A selected-probability history
Oracle: B moving state and law remain unchanged

## BW3-SAMPLE-009 — No apply-time state leak
Owner: R16 · boundaries: native_sampler, checkpoint, numerical_oracle

Exercise: Call candidate preview/probe twice then accept once
Oracle: Native staged state consumes feedback/randomness exactly once

## BW3-SAMPLE-010 — Counter state survives continuation
Owner: R16 · boundaries: native_sampler, checkpoint, numerical_oracle

Exercise: Resume a committed active partial under the same profile
Oracle: No reseeding or feedback reset at request boundaries

## BW3-SAMPLE-011 — Typical may remove argmax
Owner: R16 · boundaries: native_sampler, checkpoint, numerical_oracle

Exercise: Use probabilities 0.4 0.2 0.2 0.2 and a low typical mass
Oracle: Golden vector permits non-modal candidates rather than insisting greedy equivalence

## BW3-SAMPLE-012 — Min-P threshold stage identity
Owner: R16 · boundaries: native_sampler, checkpoint, numerical_oracle

Exercise: Apply Min-P before versus after temperature in explicit comparison profiles
Oracle: Different laws are recorded rather than mislabeled equivalent

## BW3-SAMPLE-013 — DynaTemp bounded entropy cases
Owner: R16 · boundaries: native_sampler, checkpoint, numerical_oracle

Exercise: Exercise uniform, peaked, singleton and underflow distributions
Oracle: Finite bounded output, no divide-by-zero and source-pinned golden vectors

## BW3-SAMPLE-014 — XTC threshold and tie policy
Owner: R16 · boundaries: native_sampler, checkpoint, numerical_oracle

Exercise: Exercise exact ties, threshold equality, insufficient choices and min_keep
Oracle: Pinned exclusion law and RNG draw policy reproduced

## BW3-SAMPLE-015 — Unsupported sampler is not ignored
Owner: R16 · boundaries: native_sampler, checkpoint, numerical_oracle

Exercise: Request an unavailable native selector or unknown control field
Oracle: Explicit refusal/unavailable result; no silently defaulted profile

## BW3-SAMPLE-016 — DRY plus forced syntax
Owner: R16 · boundaries: native_sampler, checkpoint, numerical_oracle

Exercise: Generate repeated protocol delimiters and names under control and prose profiles
Oracle: No hidden syntax penalty workaround; profile behavior measured explicitly

## BW3-SAMPLE-017 — Probability feedback needs more than tokens
Owner: R16 · boundaries: native_sampler, checkpoint, numerical_oracle

Exercise: Attempt restoring an adaptive state using only accepted token IDs
Oracle: Reject unsupported exact restoration unless sufficient source-certified trace exists

## BW3-SAMPLE-018 — Non-finite logits and parameters
Owner: R16 · boundaries: native_sampler, checkpoint, numerical_oracle

Exercise: Supply NaNs, positive infinities, invalid thresholds and bad state
Oracle: Controlled failure without unmasking tokens or modifying committed state

## BW3-RESTORE-001 — Whole decoder snapshot restart
Owner: R27 · boundaries: native_service, process_restart, ledger

Exercise: Restart at a committed active partial containing grammar RNG DRY and feedback state
Oracle: Declared exact continuation or explicitly unsupported capability, never silent reset

## BW3-RESTORE-002 — Checkpoint version mismatch
Owner: R27 · boundaries: native_service, process_restart, ledger

Exercise: Load saved state under a different algorithm/build/tokenizer version
Oracle: Fail before token dispatch with retained source mismatch

## BW3-RESTORE-003 — Lost native acknowledgment
Owner: R27 · boundaries: native_service, process_restart, ledger

Exercise: Commit remotely then lose local completion receipt
Oracle: Recover original operation identity and sampled result without new inference

## BW3-RESTORE-004 — Unknown checkpoint is not no-op
Owner: R27 · boundaries: native_service, process_restart, ledger

Exercise: Evict numerical state while retaining logical history
Oracle: Unavailability visible; text replay is a new lineage not exact restoration

## BW3-RESTORE-005 — Interleaving-invariant continuation
Owner: R27 · boundaries: native_service, process_restart, ledger

Exercise: Run identical seeded branches serially and with varied scheduling interleavings
Oracle: Same branch-local law/state within the qualified determinism boundary

## BW3-RESTORE-006 — Wrong receipt or branch correlation
Owner: R27 · boundaries: native_service, process_restart, ledger

Exercise: Return a valid receipt from another branch/store
Oracle: Reject without consuming the waiting result or changing local state

## BW3-RESTORE-007 — Child return crash boundary
Owner: R27 · boundaries: native_service, process_restart, ledger

Exercise: Crash after real child result/slot binding before parent resume
Oracle: Recover locals and resume once without tool replay or child regeneration

## BW3-RESTORE-008 — Late old epoch result
Owner: R27 · boundaries: native_service, process_restart, ledger

Exercise: Cancel/retry a parent and deliver an earlier child result
Oracle: Retain history; do not satisfy the newer slot

## BW3-RESTORE-009 — Duplicate accepted native segment
Owner: R27 · boundaries: native_service, process_restart, ledger

Exercise: Deliver the same committed segment/receipt twice
Oracle: Output and sampler/grammar state advance once

## BW3-RESTORE-010 — Unknown effect survives ABANDON
Owner: R27 · boundaries: native_service, process_restart, ledger

Exercise: Lose acknowledgment of a non-repeatable ACT then abandon its attempt
Oracle: Unresolved ownership and reservations remain until real reconciliation

## BW3-RESTORE-011 — Native restore versus reconstruction
Owner: R27 · boundaries: native_service, process_restart, ledger

Exercise: Deliberately initialize a new context from retained text after a supported explicit decision
Oracle: New lineage/cost recorded; no old snapshot equivalence claim

## BW3-RESTORE-012 — Draft state rollback
Owner: R27 · boundaries: native_service, process_restart, ledger

Exercise: Reject speculative draft tokens after staged grammar and sampler work
Oracle: No draft-only progress leaks to the accepted target continuation

## BW3-WORLD-001 — Real overlapping ACT dispatch
Owner: R23 · boundaries: os_isolation, scheduler, process

Exercise: Hold two owned child processes at a barrier in separate qualified scopes
Oracle: Witness intervals overlap; a sequential loop cannot pass

## BW3-WORLD-002 — Same relative path separate worlds
Owner: R23 · boundaries: os_isolation, scheduler, process

Exercise: Write src/main.py in two different enforced workspaces
Oracle: Both changes remain private and later integration conflicts are distinct

## BW3-WORLD-003 — Shared database write conflict
Owner: R23 · boundaries: os_isolation, scheduler, process

Exercise: Propose writes from different world labels to the same physical database
Oracle: Exclusive resource boundary or serialization; labels alone do not isolate it

## BW3-WORLD-004 — Shared read-only input
Owner: R23 · boundaries: os_isolation, scheduler, process

Exercise: Run siblings reading one pinned protected source snapshot
Oracle: No unintended duplication required and writes are actually denied

## BW3-WORLD-005 — Scratch and environment isolation
Owner: R23 · boundaries: os_isolation, scheduler, process

Exercise: Have siblings write temp/cache/home and inspect exposed environment
Oracle: Declared private state and credential boundaries are enforced

## BW3-WORLD-006 — Inherited handle isolation
Owner: R23 · boundaries: os_isolation, scheduler, process

Exercise: Pass or inherit a handle to a sibling/control resource by accident
Oracle: The real execution boundary prevents unauthorized access

## BW3-WORLD-007 — Global budget conservation
Owner: R23 · boundaries: os_isolation, scheduler, process

Exercise: Admit parallel work whose combined reservations exceed capacity
Oracle: Scheduler refuses excess without each child inheriting the full remaining budget

## BW3-WORLD-008 — Unknown job holds reservation
Owner: R23 · boundaries: os_isolation, scheduler, process

Exercise: Lose visibility of an owned running process
Oracle: Capacity is not released until termination/reconciliation or authorized transfer

## BW3-WORLD-009 — Planning cannot mutate shared base
Owner: R23 · boundaries: os_isolation, scheduler, process

Exercise: Execute a planning helper that tries to write source
Oracle: Real source boundary rejects the write, not just a policy mock

## BW3-WORLD-010 — Ports and device leases
Owner: R23 · boundaries: os_isolation, scheduler, process

Exercise: Contend for a shared port/device while allocating candidate scopes
Oracle: Ownership is held or allocation conflict handled before dependent execution

## BW3-WORLD-011 — Descendant process cleanup
Owner: R23 · boundaries: os_isolation, scheduler, process

Exercise: Cancel a branch whose process spawned descendants
Oracle: Known owned descendants accounted for; unknown PIDs not killed by guess

## BW3-WORLD-012 — Per-branch mutation exclusivity
Owner: R23 · boundaries: os_isolation, scheduler, process

Exercise: Dispatch two unresolved mutations against the same native branch
Oracle: Block conflict while allowing independent sibling branches to progress

## BW3-OPS-001 — SELECT does not merge
Owner: R24 · boundaries: interpreter, verifier, git

Exercise: Two alternative candidates individually pass the same contract
Oracle: One eligible reference selected under a pinned rule; no implicit patch merge

## BW3-OPS-002 — COMPOSE creates a new identity
Owner: R24 · boundaries: interpreter, verifier, git

Exercise: Combine complementary candidates with overlapping assumptions
Oracle: Fresh combined source/evidence contract; component acceptance not inherited

## BW3-OPS-003 — COMPARE retains failures
Owner: R24 · boundaries: interpreter, verifier, git

Exercise: Compare passes, failures and unknown candidates
Oracle: Full denominator and non-comparable evidence visible

## BW3-OPS-004 — CHALLENGE is a proposal
Owner: R24 · boundaries: interpreter, verifier, git

Exercise: Model emits an alarming criticism and a test command
Oracle: No accepted failure or tool execution until proper planning and observation

## BW3-OPS-005 — Protected checks cannot be weakened
Owner: R24 · boundaries: interpreter, verifier, git

Exercise: A challenged branch asks to drop a required verifier
Oracle: Reject under the immutable task contract

## BW3-OPS-006 — COMMIT needs fresh evidence
Owner: R24 · boundaries: interpreter, verifier, git

Exercise: Modify selected source after verification then publish
Oracle: Old acceptance cannot authorize the changed result

## BW3-OPS-007 — CAS publication conflict
Owner: R24 · boundaries: interpreter, verifier, git

Exercise: Change expected-old target reference before publication
Oracle: Commit fails closed and actual target state retained

## BW3-OPS-008 — No KV composition
Owner: R24 · boundaries: interpreter, verifier, git

Exercise: Request a composed answer from two independent native branches
Oracle: New inputs/context lineage established; no merge of parser/RNG/KV buffers

## BW3-OPS-009 — Pure choice avoids unnecessary generation
Owner: R24 · boundaries: interpreter, verifier, git

Exercise: Only one deterministic host action remains under the definition
Oracle: Host transition recorded as local work without fictitious model tokens

## BW3-OPS-010 — Successful return is not ABANDON
Owner: R24 · boundaries: interpreter, verifier, git

Exercise: Complete a settled verified invocation normally
Oracle: Typed successful closure preserves adoption; no false abandoned status

## BW3-OPS-011 — SAVE is not first durability
Owner: R24 · boundaries: interpreter, verifier, git

Exercise: Crash before explicit SAVE after native/effect intent
Oracle: Recovery still has required durable intent and outcome references

## BW3-OPS-012 — Publication required by output type
Owner: R24 · boundaries: interpreter, verifier, git

Exercise: Run a planning join and a publish-required group
Oracle: Only the latter waits for checked COMMIT; no global join-publication conflation

## BW3-COMPUTE-001 — Equal aggregate budget comparison
Owner: R30 · boundaries: native_metrics, benchmark, scheduler

Exercise: Compare single-branch and branched runs on the same task set
Oracle: Input/output/tool budgets matched and actual costs disclosed

## BW3-COMPUTE-002 — Physical versus logical prefix cost
Owner: R30 · boundaries: native_metrics, benchmark, scheduler

Exercise: Share a large immutable prefix across children
Oracle: Measure evaluated tokens/cache copies separately; no theoretical sharing claim

## BW3-COMPUTE-003 — Greedy clone collision accounting
Owner: R30 · boundaries: native_metrics, benchmark, scheduler

Exercise: Expand identical greedy forks with no changed inputs
Oracle: Duplicate proposals and wasted compute remain visible

## BW3-COMPUTE-004 — Budgeted progressive widening
Owner: R30 · boundaries: native_metrics, benchmark, scheduler

Exercise: Open new children only after the policy predicate becomes true
Oracle: Fan-out and total reserved cost remain bounded

## BW3-COMPUTE-005 — Early pruning false negatives
Owner: R30 · boundaries: native_metrics, benchmark, scheduler

Exercise: Audit some pruned candidates with the deeper protected check
Oracle: Pruning error disclosed, not assumed sound from a cheap test

## BW3-COMPUTE-006 — Failed and abandoned compute included
Owner: R30 · boundaries: native_metrics, benchmark, scheduler

Exercise: Generate failing candidates, cancel one and select another
Oracle: All consumed/reserved work counted and outcomes retained

## BW3-COMPUTE-007 — Verifier provenance in selection
Owner: R30 · boundaries: native_metrics, benchmark, scheduler

Exercise: A model score disagrees with an observed protected test
Oracle: Pinned rule respects evidence kinds instead of promoting model confidence

## BW3-COMPUTE-008 — Pure dedup only
Owner: R30 · boundaries: native_metrics, benchmark, scheduler

Exercise: Present identical pure deterministic tasks and superficially identical side effects
Oracle: Only declared pure computation reuse allowed; invocations remain distinct

## BW3-COMPUTE-009 — Schedule-independent seeded candidates
Owner: R30 · boundaries: native_metrics, benchmark, scheduler

Exercise: Run named candidate set under different worker availability
Oracle: Streams/inputs remain bound by identity not launch timing

## BW3-COMPUTE-010 — Unattainable feedback target
Owner: R30 · boundaries: native_metrics, benchmark, scheduler

Exercise: Force grammar to one token while requesting high surprisal target
Oracle: Finite defined control behavior without a false target-convergence requirement

## BW3-COMPUTE-011 — Challenge budget tradeoff
Owner: R30 · boundaries: native_metrics, benchmark, scheduler

Exercise: Compare extra expansion versus post-selection challenge under a fixed budget
Oracle: Both cost and verified outcome measured, no universal win asserted

## BW3-COMPUTE-012 — No hidden sampling overhead
Owner: R30 · boundaries: native_metrics, benchmark, scheduler

Exercise: Enable grammar/adaptive controls on an otherwise matched workload
Oracle: Sampling/grammar time and any throughput reduction are included

## BW3-TYPE-001 — Boolean and integer distinct
Owner: R03 · boundaries: canonical_codec, storage, return_boundary

Exercise: Round-trip true and integer one in typed values
Oracle: Both value and type identity preserved

## BW3-TYPE-002 — Text and bytes distinct
Owner: R03 · boundaries: canonical_codec, storage, return_boundary

Exercise: Round-trip UTF-8 text and same underlying byte sequence
Oracle: No coercion or accidental decoding

## BW3-TYPE-003 — Missing versus explicit absence
Owner: R03 · boundaries: canonical_codec, storage, return_boundary

Exercise: Omit a field and encode an explicit absent variant
Oracle: Canonical type contract preserves the distinction

## BW3-TYPE-004 — Large integer and precise decimal
Owner: R03 · boundaries: canonical_codec, storage, return_boundary

Exercise: Round-trip large signed integer and scaled exact decimal
Oracle: No float rounding or normalization that loses declared information

## BW3-TYPE-005 — Empty values allowed
Owner: R03 · boundaries: canonical_codec, storage, return_boundary

Exercise: Round-trip empty string bytes list tuple and record
Oracle: Valid empties remain distinct from missing payload

## BW3-TYPE-006 — Duplicate encoded fields
Owner: R03 · boundaries: canonical_codec, storage, return_boundary

Exercise: Decode a record with duplicate field names
Oracle: Reject canonical corruption; never last-key-wins

## BW3-TYPE-007 — Noncanonical numeric/length forms
Owner: R03 · boundaries: canonical_codec, storage, return_boundary

Exercise: Decode leading-zero lengths, alternate integer forms and nonfinite floats
Oracle: Reject instead of silently normalizing signed source bytes

## BW3-TYPE-008 — Torn trailing versus committed corruption
Owner: R03 · boundaries: canonical_codec, storage, return_boundary

Exercise: Fault the real ledger before and inside a committed record
Oracle: Declared tail recovery only; corrupted committed evidence blocks

## BW3-TYPE-009 — Unknown canonical version
Owner: R03 · boundaries: canonical_codec, storage, return_boundary

Exercise: Restore a typed value with an unsupported codec/schema version
Oracle: Explicit incompatibility, not a guessed migration

## BW3-TYPE-010 — Single ledger writer
Owner: R03 · boundaries: canonical_codec, storage, return_boundary

Exercise: Attempt two product writers against one run
Oracle: Second writer is denied at a real ownership/locking boundary

## BW3-TYPE-011 — Artifact before reference
Owner: R03 · boundaries: canonical_codec, storage, return_boundary

Exercise: Crash between staging/publishing bytes and appending their event
Oracle: No event references missing unpublished bytes; orphan residue is not success

## BW3-TYPE-012 — Native state not generic codec claim
Owner: R03 · boundaries: canonical_codec, storage, return_boundary

Exercise: Serialize the reference snapshot but lack a native state export
Oracle: No native restart capability issued from the reference codec result

## BW3-FEATURE-001 — Title branch does not pollute Builder
Owner: R13 · boundaries: native_generation, templates, views

Exercise: Generate headline while Builder continues another scoped task
Oracle: Separate inputs/context histories and normal tracked invocation ownership

## BW3-FEATURE-002 — Factual status independent of narration
Owner: R13 · boundaries: native_generation, templates, views

Exercise: Model writes a status note claiming success during unresolved work
Oracle: Ledger-derived factual status remains unresolved

## BW3-FEATURE-003 — Template pinned across partial continue
Owner: R13 · boundaries: native_generation, templates, views

Exercise: Edit template after a token-limited committed partial
Oracle: Existing output retains original grammar/template/profile identity

## BW3-FEATURE-004 — Summary cites omissions
Owner: R13 · boundaries: native_generation, templates, views

Exercise: Produce summary with missing evidence or unresolved operations
Oracle: Required omissions and exact source references retained

## BW3-FEATURE-005 — No display-time hidden generation
Owner: R13 · boundaries: native_generation, templates, views

Exercise: Open inspect/history/tree repeatedly
Oracle: No added model/tool work or changed budget

## BW3-FEATURE-006 — Human answer to exact epoch
Owner: R13 · boundaries: native_generation, templates, views

Exercise: Deliver approval after the original wait was superseded
Oracle: History retained; current attempt not authorized by stale answer

## BW3-FEATURE-007 — Reasoning capability honesty
Owner: R13 · boundaries: native_generation, templates, views

Exercise: Backend offers plain text but no native reasoning stream
Oracle: Generated analysis labeled correctly; unsupported channel remains unavailable

## BW3-FEATURE-008 — Same features one or two services
Owner: R13 · boundaries: native_generation, templates, views

Exercise: Run typed headline/tool/summary flows with shared and separate role services
Oracle: Same semantics without claiming cross-service snapshots or free prefill

## BW3-MTP-001 — Separate worktree preservation
Owner: R34 · boundaries: native_speculative, numerical_oracle, worktrees

Exercise: Qualify constrained target-only work while an MTP worktree exists
Oracle: No regression or silent configuration changes to either source tree

## BW3-MTP-002 — Target-law speculative validation
Owner: R34 · boundaries: native_speculative, numerical_oracle, worktrees

Exercise: Enable draft proposals with stochastic target sampling
Oracle: Distribution/accepted-prefix correctness proved under pinned native law, not token matching alone

## BW3-MTP-003 — EOS rejected suffix
Owner: R34 · boundaries: native_speculative, numerical_oracle, worktrees

Exercise: Draft beyond a target EOS then reject the suffix
Oracle: No extra grammar/history/RNG progress from discarded suffix tokens

## BW3-MTP-004 — Unavailable combination refusal
Owner: R34 · boundaries: native_speculative, numerical_oracle, worktrees

Exercise: Request GBNF plus an unsupported backend speculative path
Oracle: Explicit unavailable result with no hidden switch to a different execution law
