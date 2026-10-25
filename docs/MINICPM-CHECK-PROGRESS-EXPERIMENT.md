# MiniCPM check-readiness experiments

The remaining shell workflow is still unresolved. Four new five-objective probes
tested verification guidance and selected-check feedback with unchanged MiniCPM
weights. None improved on the existing default. The default instructions and
feedback remain unchanged; check-readiness feedback is available only through
an explicit experimental host configuration.

| Probe | Saved programs independently correct | Whole workflows independently passed |
| --- | ---: | ---: |
| Unchanged default control | 5/5 | 4/5 |
| E: generic verification guidance | 5/5 | 4/5 |
| F: guidance plus current check-readiness feedback | 4/5 | 3/5 |
| G: check-readiness feedback alone | 2/5 | 2/5 |

These are development observations on five discovery objectives per probe,
not a failure-rate estimate from a broad sample. The four probes share the same
model and strict CUDA runtime. Historical results on another host/runtime remain
separate; they cannot isolate the effect of these changes.

## What the traces established

The original selected-check workflow reports an overall failure until an explicit
finish request. Before that request it returns the reason `explicit finish request
required`, without reporting the current selected-check results. This concealed
useful progress even when a named check had actually passed.

The prototype computes readiness from the existing visible, settled execution
receipts and current workspace. It reports `check_status` separately from the
overall workflow status. A passed check still leaves the workflow unverified
until the model requests finish. Failed, missing or stale checks remain failed.
It does not execute an extra command or change the acceptance policy.

Accurate feedback did not establish better model behavior. In F, the model left
an unquoted shell expansion unchanged, tested simple filenames instead of the
requested difficult filenames, and claimed completion. Its own selected checks
passed; the independent S³ checker failed the saved program. G also produced an
incorrect Python artifact despite passing its own checks. These observations
show why model-selected tests and independent task correctness remain separate.

The status-repair workflow also continued making exploratory commands instead
of finishing. Merely adding instructions or exposing check state did not solve
that behavior. The next probe should examine the size and usefulness of the
model-visible tool feedback and independently test the strength of its proposed
checks, with fresh task variants. Those are hypotheses and next work, not
measured improvements.

## Explicit experimental configuration

For an agent-created project launch, the opt-in is:

```python
launch = build_launch(project, task, connection, branch=branch, project_files=True)
launch['config']['verification']['progress_feedback'] = True
save_launch(state, launch)
```

There is no new CLI flag. Ordinary launches omit this setting. The selected
policy identity binds the opt-in, and a saved launch retains its original
configuration. Do not change this setting or runtime source to resume an
already admitted experiment. The final explicit configuration is covered by
CPU admission and execution checks; the prototype GPU results do not qualify it
as a behavioral improvement.

## Evidence and limits

The probes used 65,536 context tokens, thinking off, at most 512 output tokens
per request, a 120-second task guard and 256 interpreter steps. The 12-request
limit was per model action rather than a matched global cap; actual request
counts remain in the evidence. No model weights changed and no candidate was
promoted.

The selected-check mechanics, actual shell namespaces, stale-check refusal,
explicit finish gate, bounded feedback, grammar/restart mechanics and existing
CLI/HTTP paths passed 58 focused CPU checks. A separate manifest round-trip
check passed and refused a non-boolean opt-in. These checks use scripted model
choices where HTTP mechanics require a model fixture; they are not proof of
MiniCPM skill.

G's timed-out request was observed as cancelled by its original coordinator,
without durable commitment. Its original failure and journal were preserved.
Output recovery was refused, and no fresh generation or tool replay was sent.

[Counts, source/runtime identities and evidence hashes](../validation/minicpm-shell-investigation-20261024/check-progress-20261025.json)
contain no raw task responses or model files. The earlier
[shell investigation](MINICPM-SHELL-INVESTIGATION.md) remains the reference for
the accepted default's four completed workflows.
