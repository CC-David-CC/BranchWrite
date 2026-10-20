Guarded application into a NEW owned copy is implemented; in-place checkout
publication is deliberately not claimed. The original checkout is never modified.
Archive SHA pin, full input inventory, per-file preimages and final output
inventory are checked. Linux renameat2 NOREPLACE prevents replacing a destination
created at the publication race. Prepublication flush failure leaves no output.

Eight new test-first cases and251selected regressions pass. Fresh installeddev12
on llm-49 passes61controls. Its public apply command consumed the actual SC11 Q8
export and produced exact bytes matching the earlier applied project that passed
six original methods and200isolated independent cases. This was offline handoff
validation, not a new GPU inference run. No numerical oracle/certification.

A malformed manifest initially escaped as AttributeError; the red test is retained
and it now gives a controlled ValueError. Dev11 was an intermediate installed
build before that correction; finaldev12 is separately pinned and installed.
Wheel4202ab133689352cba46ea328776991e7146900bda1ed4ed9f6c36cef5f51aa9.

Persistent apply receipts, idempotent lost-ack reconciliation, process-kill and
power-loss recovery remain outstanding. In-place Git integration and broader
autonomous coding projects remain within the active objective.
