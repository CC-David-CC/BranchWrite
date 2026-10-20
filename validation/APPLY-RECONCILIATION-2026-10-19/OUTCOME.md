Apply acknowledgment reconciliation is implemented with a co-published directory
xattr receipt binding operation, archive, destination, source, final inventory and
root device/inode. Exact retries return the same result; unrelated/copied/modified
directories are refused. It is destination-scoped metadata, not a workflow log.

Six new distinguishing cases pass, including real subprocess os._exit before
rename and after rename/before parent flush, followed by a new process retry.
257selected regression methods pass. After that run, a small malformed-receipt
type guard and documentation correction were added. Final installeddev13 passes
67controls, including both subprocess crash cases. Wheel:
4e01b1fdc54031e1a0ae8b321abedb48434aff9aea071e769d39fe78d862614e.

No new GPU inference was run; this is offline publication/reconciliation.
Power-loss testing, orphan staging cleanup and in-place checkout/Git integration
remain outside the implemented promise. Existing outputs without metadata remain
preserved and refused, never retroactively claimed.

Next: project discovery and a broader multi-file autonomous coding task using the
real installed client and saved prefix. The full agent objective remains active.
