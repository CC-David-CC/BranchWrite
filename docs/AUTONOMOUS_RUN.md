New project/task commands: [CODING_LAUNCHER.md](CODING_LAUNCHER.md). Dynamic grammar admission and Q8 evidence supersede the older startup-only/deferred statements below; see STANDALONE_CODING_STATUS.md for executed scope.

Current standalone-agent goal, roles and rerun limits: [STANDALONE_AGENT.md](STANDALONE_AGENT.md).
Historical catalogue snapshots below are not a substitute for current executed evidence.

# Current delivery goal: a push-button autonomous coding run

Owner direction,2026-10-18: aim at a push-button autonomous coding run.
A .bw file is the workflow recipe, not a KV-cache file. BranchWrite consumes the
recipe and uses Context COW for preserved native model computation. The original
VC00-VC09 and G1-G5 qualification work remains separate and outstanding.

The immediate acceptance is one Linux CLI invocation which receives a task and
owned source workspace, lets the real Q4 model select registered tools, applies
only granted edits, runs actual tests, feeds failures back and stops with a clear
verified/unverified/unfinished result. No implementer-supplied patch or manually
chosen next action during that run. A bounded example does not establish general
coding ability; changed and unfamiliar tasks must follow.

## What the executable core currently provides

- One Interpreter on FrameKernel and RuntimeLog; run and step use that driver.
- TEXT/VALUE, EXPAND, PLAN, ACT, tool-feedback/cow-source TRANSFORM, the explicitly
  named unit-tests-and-finish VERIFY policy and bounded REPEAT.
- Type/name/handler preflight for the whole program, before model/tool dispatch.
- Frozen PLAN bytes are the exact bytes ACT uses. Live grants and preimages are
  rechecked; changed worlds cause known rejection, not a silently updated plan.
- Partial native replies remain inside ModelOutput FLOW. COW owns thinking,
  sampling, grammar state, controllers and canonical context.
- Invalid tool proposals become feedback. Unknown post-effect outcomes retain
  their original operation IDs and require reconciliation, never automatic resend.
- Completed calls and scopes recover from the existing ledger. Caller-visible
  values derive only from resumed predecessors. No extra workflow/state database.

Advanced syntax (including BRANCH/PARALLEL/COMMIT/ON/ABANDON handlers) is not yet
executable. Unsupported handlers are refused at admission, including late ones.
The checked parser still recognizes the full language. This increment does not
make the complete product catalogue or image-controller workflows pass.

## Default coding setup

New coding setups default to greedy and the worked examples: temperature0,
Min-P0, Top-K0, Top-P1 and DRY0. The owner changed this policy on2026-10-18.
Explicit generation_profile('min-p') and generation_profile('dry-min-p') are
available for host-selected fallbacks after verified failures. These helpers do
not automatically retry effects or change a saved controller. It uses the named
BW_TOOLS thinking grammar. New grammar admission uses4096 thinking tokens.
The default transport allowance is32 chunks of2048 output tokens;it is a finite
run resource bound,not a desired final-answer length. EOS stops shorter answers.
See THINKING_LADDER.md for defined escalation levels and integration status.

Use examples/coding.bw as the generic workflow. Omit the `profiles` field from
the host manifest to select the default control profile. An explicitly supplied
profiles mapping is preserved exactly: it is the way to select another sampler
or an intentional greedy control. Existing saved controllers are never edited
when defaults change; resume with their pinned code/config.

For a new context, add `"bootstrap": "coding"` to the cow object and use mode
`ask`. The CLI creates an authorized namespace and context-only root containing
the live tool schema plus the three examples. It uses original journaled setup
IDs/bytes, so a setup retry does not repeat acknowledged prefix creation. The
examples alone are10511 actual tokenizer tokens; complete prefix size depends on
the live schema/template and is measured separately. No current task answer or
protected workload verifier is inserted.

For an existing prepared context, omit bootstrap. That preserves exactly the
existing source; the CLI does not secretly add examples to a saved native state.
The server must already have the compatible BW_TOOLS startup grammar; this is
not an inline-grammar admission endpoint. Source-checkout execution is currently
supported; a standalone installed distribution remains packaging work.

## Running a workflow

On Linux, with the BranchWrite checkout on PYTHONPATH:

    python -m branchwrite check /absolute/path/job.bw
    python -m branchwrite run /absolute/path/job.bw --config /absolute/path/host.json --state /absolute/path/new-owned-run

The state directory must be outside the user's source checkout. It is mode0700.
BranchWrite copies the source into state/world/workspace. Edits go there; they do
not modify or publish the original checkout. Inspect the result before publishing.
Run the same command to resume the same work. Do not change its program/config.
Use `step` instead of `run` for one interpreter transition. New run=new state path.

The JSON host manifest is setup configuration, not an alternate workflow ledger:

```json
{
  "schema": 1,
  "source": "/absolute/path/source",
  "run_id": "my-coding-run",
  "grant": {
    "edit_paths": ["calc.py"],
    "read_paths": ["calc.py"],
    "create_paths": [],
    "allow_tests": true
  },
  "bindings": {
    "task": {"type": "Text", "value": "Repair the requested behavior and run the tests."}
  },
  "cow": {
    "endpoint_url": "http://127.0.0.1:PORT",
    "endpoint_pin": "actual-host-bound-identity",
    "model_contract_id": "actual-model-id",
    "execution_profile_id": "actual-execution-id",
    "eos_tokens": [248044, 248046],
    "branch": "new-coding-branch",
    "mode": "ask",
    "bootstrap": "coding"
  }
}
```

Use actual identities/EOS IDs for the selected service/model. Set the API key in
BW_COW_API_KEY, never in the manifest. Endpoint pinning is the existing host
binding, not independent server attestation. COW must already run. Without coding bootstrap, the named
branch must have the declared boundary: ask=context-only root;
append_user=consumed stopped turn. This CLI does not guess boundaries or rebuild
contexts. The smoke runner creates its own service; its default mode uses the same public
CLI bootstrap and default profile as normal new coding runs.

BW_TOOLS is a startup thinking grammar. New setups use
coding_defaults.grammar_registry(actual_registry), whose final GBNF places the
tool name before its arguments. ToolRegistry.model_gbnf() derives that syntax from
the same registered tool definitions as the JSON Schema and host validation.
Existing JSON parser checkpoints must not be loaded under the new grammar;
create a new context. The smoke runner retains an explicit
--grammar-layout json-schema control. New thinking budgets are4096;
request_tokens is a total native request budget, not the thinking budget. Existing
512-token successes/controllers are unchanged. Other COW sampler settings can be
supplied in a profile settings mapping; this increment has no new sampler-matrix
qualification. General inline schema registration remains absent.

Example body, inside FLOW coding / END:

```text
REPEAT attempts max=16 until=verified exhausted=stop
EXPAND decide from=current task=task profile=control -> proposed
PLAN freeze from=proposed against=world -> plan
ACT perform plan=plan -> outcome
TRANSFORM advance input=proposed contract=cow-source -> current
TRANSFORM feedback input=outcome contract=tool-feedback -> task
VERIFY check input=outcome contract=unit-tests-and-finish -> verified
END
```

The host binds current to the exact observed COW source head on first admission;
restart retains that original source binding and subsequent recorded returns.
Uncertain work is never rebased onto the branch's newest tip automatically.

## Results and limits

Exit0: this run completed and its configured verifier passed.
Exit1: workflow completed without verification (including repeat exhaustion).
Exit2: invalid setup/program or explicit rejection/error.
Exit3: bounded stepping/model budget ended with work still retained.
Exit4: original external operation is unresolved; reconcile before continuing.
Stdout is a small JSON status with a result-artifact hash. Full model/tool results
stay in the private ledger/artifacts. Reopening a completed run returns its old
receipt; it is not a fresh claim about later external workspace modifications.

unit-tests-and-finish means a real successful nonempty registered unittest run,
unchanged current workspace inventory and an explicit finish request. Test paths
must not be editable by the grant. The model's finish request alone cannot pass.
This is a bounded named policy, not proof of arbitrary user requirements and not
a hardened verifier against hostile candidate code forging test-runner output.
A stronger separate protected acceptance boundary remains required for that scope.
Code executes only through the existing sandboxed Executor, not on the driver.

Original COW numerical/restart/resource certification, power loss, platform matrix,
long soak, advanced workflow forms, image-aware tool feedback and broad unfamiliar
workloads remain outstanding. Q8 is deferred; chat stays OFF. Private LAN Git only.

## Autonomous workload status

The owner requested a fresh autonomous ladder from Basic Agent Loop H00.
Guided H00-H06 history does not count toward these runs. The generic CLI repair
smoke is not a catalogue pass. Autonomous H00-H06 pass through the separate client;
H07-H12 remain unrun (7/13). Ubuntu Agent Baseline is not started. See validation/CURRENT-CATALOG-STATUS.md for the next bounded target.

## File-only tasks

New host setups can select examples/file-task.bw and the explicitly named
file-readback-and-finish contract with protected host file hash expectations.
See FILE_COMPLETION.md. This does not weaken unit-tests-and-finish or turn a
model finish request into acceptance. The source/receipts must actually agree.

## Browser capture through the CLI

A new supplied-page task can use examples/page-task.bw with host browser and
capture_paths settings. CLI returns actual image artifact paths/hashes and source
revisions; the model sees capture receipt metadata before finishing. See
FILE_COMPLETION.md and REMOTE_CLIENT.md for policy, setup and scope. With an explicit image-feedback profile, actual captured pixels reach the next
EXPAND; the generated-page workflow passed H03. Explicitly granted interact_page click/fill recipes now have bounded CLI tests;
interaction-state-aware completion and one live Q4 H06 click workflow now pass.
Autonomous fill/input H07 remains unrun. See IMAGE_INPUT.md and IMAGE_FEEDBACK.md.

## Host-bound file versions

New model proposals omit source_sha256 for replace/capture/interact. The host
binds the latest actual observation into bw.tool-plan.v2 and preserves all stale
file and ownership checks. See OBSERVED_SOURCE.md. New contexts use the updated
same-three-example prefix and startup grammar. Old pending workflows retain
their original pinned implementation; no automatic migration/resend is provided.


## Named browser viewports

An optional host browser.viewports mapping grants up to eight named fixed
screen sizes,for example desktop=[640,480] and phone=[360,640]. Include the
default width/height in that menu. The live schema then requires a viewport
name on capture_page and interact_page. Models cannot request arbitrary sizes.
Plans and receipts bind the selected name,actual PNG dimensions,and exact
source/resource/action bytes. Completion can require the same page observed at
multiple approved sizes;missing,stale or relabelled observations do not qualify.
The default single-viewport interface remains available when no menu is supplied.

H12's actual model selected the CSS repair and both-size interactions;its
protected checks and independent delivery audit passed. This is bounded evidence,
not proof of arbitrary responsive-design ability. See the current catalogue
status and AUTONOMOUS-H12-Q4-2026-10-18.json for fingerprints and limitations.
