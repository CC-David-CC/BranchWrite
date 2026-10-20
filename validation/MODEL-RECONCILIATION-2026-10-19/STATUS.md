# Explicit durable model-output reconciliation

API ticket PASS on CPU HTTP fixtures; CLI command and interrupted real-GPU workflow remain pending. This branch is not integrated into the installed client.

CowClient.reconcile_generation requires an original endpoint-bound journal intent. A complete saved answer is read offline. Otherwise it obtains and validates durable server proof before replaying exactly the original bytes. The replay receipt must equal the proof before publishing the answer. Unknown, failed or non-durable requests remain unresolved. Tool effects are outside this operation. Existing automatic workflow stepping and replay_original semantics are unchanged.

Executed: eight focused controls and existing model dispatch/durable answer/image lost-ack/fork receipt coverage, 42 methods total PASS, no skips. G0 51 PASS. Three deliberately broken variants detected (one causes an error, two assertion failures). These are CPU fixtures, not GPU inference evidence.

Initial test setup omitted a declared FlowModel plan; corrected setup was then run against the unchanged baseline: six expected missing-method errors. The first broader runs missed existing proxy/helper modules and an implementation-test path in the test mirror; those failures remain retained. The complete environment rerun passes unchanged assertions.

Next: test-first CLI reconciliation bound to a dispatched model frame in the original saved run, then a process-interrupted coding workflow. Do not silently replay unknown work or reconcile tools through this route.

## CLI ticket PASS (CPU HTTP/subprocess)

The reconcile command binds the private saved launch to the original program and host-config digest, takes the existing ledger read lease, and requires one open dispatched model frame with matching journal bytes, source and endpoint. It retrieves proven durable output without changing the workflow ledger. Existing resume/step consumes that exact local result. A live writer, changed grants, tool operation and unowned operation are refused; a known failed/non-durable model operation remains exit4.

Six new CLI methods pass. Broader launcher/status/run/dispatch/recovery coverage:76methods PASS,zero skips. This count includes prior API controls; do not add overlapping totals. Guide updated in docs/CODING_LAUNCHER.md. dev17 packaging follows; installed-client and interrupted real-GPU coding qualification remain pending. No interpreter migration is implemented.

## Installed controls and live SC18

Fresh dev17 wheel:292ecffe071bd13d082f0480d7e77e9ebbf9f1f92c0ee17451581e03c12c4840. Fourteen recovery controls pass using the installed package with no BranchWrite source root on PYTHONPATH.42installed Python modules match wheel bytes. Counts overlap source tests.

Test-only lost-ack proxy now optionally selects the first actual bwnative operation, leaving setup and explicit-ID behavior unchanged. New distinguishing control is red on the old proxy and green after the change.20affected source controls pass; an earlier attempt omitted COW_CLI_SCRIPT and is retained as an environment failure.

SC18 real Q8 run is active:llm-49 installeddev17, llm-60 candidate-profile server, new interval repair. After one real durable model completion was deliberately withheld, a new reconcile process recovered exact output with the workflow ledger unchanged. Native PID704194 reported1232forward tokens both before and after reconciliation. The autonomous resume is still running; no final coding PASS yet. This is lost-ack/network-interruption recovery,not SIGKILL or tool-effect crash qualification. Terminal-only independent audits are queued.

## SC18 complete, status guidance source-tested

Real Q8 lost-ack recovery and new interval repair PASS in installeddev17. Six logical model calls,5216outputs. Active CLI phases:21.64seconds first interrupted call,0.401seconds reconciliation,302.51seconds autonomous resume;324.55seconds summed active CLI time,excluding steering barriers and server startup. Exact recovered output,unchanged workflow ledger andzero native forwardwork during reconciliation. Original12tests and1000independent cases passed;review/export/apply/exact-retry/offline resume passed. Initial independent audit failed before discovery because its separate test copy lacked a package marker. It is retained; the corrected baseline ran12methods with10failures,and candidate passed without changing original tests or model output. All processes exited0 and credentials retired. Details/private receipts:validation/SC18-2026-10-19. Not SIGKILL/tool-effect crash or full numerical/release qualification.

Status-guidance ticket:three new distinguishing controls red on baseline;10status methods plus6CLI recovery controls pass. Read-only status adds model-specific reconcile/resume argv and keeps tool effects separate,without opening the COW client or changing any recorded state. Source version moves todev18; it is not packaged or GPU-qualified. Dev17 wheel and completed task evidence remain unchanged.

Next environment gap:built-in Executor.run_tests currently assumes tests is a Python package. Test and fix common package-free discovery without changing sandbox isolation,source bytes or reference assertions. This is a tool-environment improvement,not a model-training failure.
