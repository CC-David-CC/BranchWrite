# Separate answer, reasoning and formatting lessons

S³ defines three distinct learning conditions:

- **Answer:** score whether the answer is correct. Direct and reasoning modes are
  separate; reasoning mode requires its own verified reasoning target and checker.
- **Format:** give the model the correct answer, then score whether it preserves
  that content in the requested task-specific format.
- **Composed:** solve the task and produce the correctly formatted answer. Direct
  and reasoning versions are separate conditions.

Ask the installed S³ package what the current validated policies are:

```bash
branchwrite learning levels
```

This command needs the `skills` optional dependency, but no COW connection. Its
JSON is a guide to condition names, not evidence that any model passed them.

S³ authors and verifies a practice lesson with an exact task checker, renderer,
tokenizer and lesson spans. PCC remains the authority that tokenizes/adopts the
lesson and applies its loss mask. A verified S³ lesson file can be handed to BW:

```bash
branchwrite lesson submit /owned/verified-lesson.json \
  --operation-id lesson-001 --train-now --mode lora --rank 4
```

The PCC server still checks the model contract, lesson evidence, target policy,
token limit and training policy. `--train-now` requests a candidate update; it
does not accept or promote that candidate. Use the registered learning round to
measure held-out learning and forgetting, review the report, and preserve a
working parent only under the installed PCC policy.

BW's `learning drive` follows actions advertised by PCC. It does not create
lessons from failed evaluations, choose a format checker, change optimizer
settings, or promote weights. S³ owns test definitions and lesson evidence; BW
owns the human/agent client and task workflow; PCC owns model state, training,
evaluation masks and candidate decisions.
