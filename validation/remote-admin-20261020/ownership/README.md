# RM02 endpoint ownership, dev46

16 CPU checks and 8 repeated installed SSH checks pass. Two additional real
process/VM cases pass: while one SSH command held the endpoint, a second client
with a different alias and timeout was rejected before recording/sending a new
command; after a deliberate client exit73 AFTER a real receipt was durable but
BEFORE lease completion, another client validated that receipt, released the
reservation and proceeded. Re-reading/repeating the old operation produced the
same stored result; the guest append marker was not duplicated.

Target resource identity uses the canonical literal endpoint (host, port), so
aliases, user names, credentials and timeout changes cannot bypass ownership.
The file lock prevents overlap. A separate durable reservation survives process
closure. A validated receipt for its exact original intent is needed to release
it. A dead process or released file lock alone is not a successful remote result.
A wrong thread or stale lease cannot modify its reservation. Unknown outcomes
remain blocked; there is no force-release or replay-under-new-ID option.

The scope is host-local coordination on llm-49, whose test VM is loopback-only.
This is NOT cross-client-host fleet locking. A declared physical target reachable
through several addresses/ports would need an explicit shared resource identity;
cross-host clients need resource-native coordination or a shared trusted broker.
Do not advertise those as complete. The current candidate remains outside the
model-facing registry and ordinary CLI.

Installed validation initially failed BEFORE SSH because the existing app state
container was mode0775. The API now accepts a safe owned0755 container while
requiring private0700 target state. Actual group-write permission was removed
from the owned BranchWrite app container (0775 ->0755), rather than relaxing the
check. The first and second failed attempts remain in the raw archive. No SSH
command ran for either failure. Old interactive session content was unchanged.

Known-receipt crash recovery is demonstrated. Abrupt death BEFORE receipt
publication remains unknown, not automatically recoverable. Persisted reservation
keeps later mutations blocked. No model, GPU, G-gate or general exactly-once claim.
