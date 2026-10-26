# Optional structured tool grammars

BW now offers a Lark version of its generated tool grammar. It keeps action
and array structure in the parser instead of compiling an entire bounded
array into one lexical expression. In a CPU diagnostic, the original matcher
exhausted 250,000 lexer states at 706 tokens. The structured version accepted
the saved 512 tokens plus 4,096 synthetic tokens with unchanged parser limits.
The synthetic continuation is not the missing original response.

## Use the supported path

Use the matching [PCC Lark feature](https://github.com/CC-David-CC/Private_Context_COW/blob/feat/lark-grammar-20261026/docs/LARK-GRAMMARS.md).
For a new BW `run` configuration with inline grammar registration, add this
field to the existing `cow` object:

```json
{
  "grammar_registration": "inline",
  "grammar_syntax": "lark"
}
```

This fragment is not a complete host configuration. Keep the existing endpoint,
model/profile identities, branch, EOS, mode, grants and task bindings. Run the
ordinary command with that full configuration:

```sh
python -m branchwrite run task.bw --config host.json --state new-run
```

A person or agent can also build the same immutable definition in Python:

```python
from branchwrite.coding_defaults import grammar_registry
definition = grammar_registry(host_tool_registry, direct=True, syntax="lark")
```

Lark generation requires optional **llguidance 1.9.1** in the BW environment;
PCC already pins that version for its parser. It is imported only for this
explicit option. Missing or different versions fail clearly, without falling
back to a different grammar. Omitting `grammar_syntax` retains the previous
GBNF payload. The full host configuration binds registration and replay, so
changing syntax on an existing run is refused even after it has completed.

`ToolRegistry.model_lark()` starts from the same grant-derived GBNF definition
and uses the pinned converter's parsed rule objects. It preserves literals,
field order, bounded repetitions and escaped text; action/array rules remain
parser rules while strings remain lexical terminals. References update through
the parsed nodes, never text replacement inside user-visible literals.
The normal host parser and Executor still enforce grants, file preconditions,
byte limits, checks and completion. Grammar registration grants no effects.

## Recovery and what is actually proven

The real CLI/HTTP tests cover new contexts and explicit retained-context tasks,
immutable registration, completed offline replay with an unchanged ledger,
and refusal to reopen the same run under changed syntax. A scripted CPU
backend drives those tests. They do not establish autonomous MiniCPM success.

Do not change a saved partial generation's grammar. First reconcile its
original operation through its recorded ID and bytes. If it remains unknown,
preserve that state and its evidence; do not resend it as a fresh operation or
mark it successful. A separate new task with new IDs may use this grammar,
but it is a new run rather than a completed recovery of the old one.

The [qualification receipt](../validation/lark-grammar-20261026/qualification.json)
includes the diagnostic and log/source hashes. Tests accept a 4,096-entry
array and reject 4,097; a deliberate one-entry bound relaxation is caught.
The old default payload is checked against its original implementation and
the PCC old-format controller cannot be restored under the new format.

Preserving all rules as parser rules hit a separate parser-item limit; preserving
only some action alternatives masked an observed valid token. Those attempts
are retained as failed diagnostics. The adopted version preserves all action
alternatives and array rules, and keeps string lexemes. Arbitrary long strings,
browser interactions and a real GPU workflow on this path still require their
own qualification. The original failed BW journal remains unchanged.
