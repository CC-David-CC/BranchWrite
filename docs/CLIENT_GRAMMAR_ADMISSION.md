# Client grammar admission ticket
Use the existing OperationJournal and real HTTP transport. Record exact request
bytes before sending. Grammar definitions are immutable metadata,not a second
conversation. The server must durably bind a registration operation ID to its
definition digest and returned group; conflicting reuse fails across restart.
An interrupted registration may explicitly replay only its original ID/bytes.
A completed replay returns metadata locally,not a fabricated generation receipt.

Before coding inference, register the host-generated grammar_registry(registry).
Map each original named state in admitted thinking profiles to the returned
content-derived public state name. Persist the mapping with host admission.
Do not silently rebind a saved workflow or change a live controller's grammar.
Unsupported CLI transport fails explicitly. No server/native imports on clients.
Authentication and actual tool grants remain separate from grammar syntax.
No unjournaled POST,stateless transcript fallback,or API key in metadata.

Status:test-first requirements; register_grammars missing. Actual COW HTTP fixture
tests must run with server dependencies. Later live CLI runs remain on llm-49.

## Implemented bounded result
The earlier test-first status is historical. Client implementation and automatic
CLI admission now exist. Select cow.grammar_registration="inline" with
cow.bootstrap="coding" and mode="ask". Server must explicitly enable
--grammar-store /absolute/private/directory together with --text and --api-key.
Unsupported server/transport fails explicitly. No static-grammar fallback.

Pure workflow preflight precedes registration. Registration uses the existing
OperationJournal; lost acknowledgment replays only its original ID and bytes.
The server durably binds that ID to exact definitions. Returned content-derived
states are frozen into ModelAdapter identity. Thinking policy keeps logical state
names; every rung resolves through the same admitted mapping. Completed workflow
reopen uses retained registration metadata and can succeed with the server offline.

103 CPU/HTTP/CLI checks passed,including an actual subprocess CLI registration,
command completion without expected artifact hashes,and unchanged-ledger offline
replay. Actions in that CPU integration are host-scripted. They do NOT establish
autonomous coding or GPU correctness. Live cross-host Q8 validation is pending.
No cumulative G1–G5 qualification; all source and evidence remain private LAN.
