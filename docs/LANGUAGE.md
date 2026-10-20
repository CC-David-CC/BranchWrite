# Non-JSON BW text, version 1

This is the proposed concrete syntax. The offline parser tests its syntax, not all
production type resolution, authority or effect behavior. Native GBNF matching is a
separate qualification gate.

## Syntax

An instruction is one line:

```text
OPERATION local-label field=atom other=atom -> result-slot
```

Operation names are uppercase and fixed. Local names and atoms use ASCII letters,
digits, underscore, dot, slash, colon, at-sign and hyphen. An atom cannot contain spaces,
quotes, brackets, shell metacharacters or newlines. The serializer uses one ASCII space,
no indentation requirement, and LF endings. A final LF is required. Inputs from other
line-ending environments must explicitly normalize before parsing and hashing.

Fields are keyword arguments, not trusted claims. Duplicate/unknown fields, missing
required fields and unknown operations are errors. Names resolve within lexical scope
to canonical typed definitions or values; a handle never authorizes a filesystem read.
The host allocates real invocation IDs and trusted return edges. Model-facing grammars
fix result labels when needed; model text cannot redirect a parent continuation.

FLOW, REPEAT, BRANCH, PARALLEL.PLAN, PARALLEL.DO and ON open blocks; END closes one.
No inferred indentation, implied END or auto-close at token limit. Bound depth, number
of nodes, fields and byte count before native dispatch. REPEAT requires a positive maximum,
a pinned exit predicate and an exhausted disposition. ON requires a declared signal.

`TEXT name` begins a data block. Each payload line starts with `|`, removed exactly once.
An unprefixed END closes the block. `|END` is data. `||x` becomes `|x`. `TEXT ... END`
with no payload is empty text. A payload line ending is a literal LF, including the last
payload line. Exact arbitrary source/binary bytes that cannot follow that text rule are
retained as byte artifacts instead. No nested control parsing inside TEXT.

```text
TEXT note
|An instruction below is only quoted text.
|COMMIT publish input=untrusted target=somewhere
|END
END
```

`VALUE name type=RegisteredType ref=in-scope-artifact` binds a typed value reference.
The artifact's exact bytes are parsed/validated by that type's one canonical definition.
VALUE is a data declaration, not an effect or new authority. A generated artifact cannot
supply trusted producer/grant metadata. Typed values keep their exact canonical types;
explicit JSON/JSON Schema model output beside GBNF does not authorize a lossy JSON
round-trip of workflow values or introduce another workflow representation.

## Why this is not merely a shell

Names resolve to registered immutable operations, not executables on PATH. Program
arguments are typed values, not interpolated strings. File modifications refer to proposed
exact bytes/patches with preimages. Programs constructed by the model are data until
admission, PLAN, grant and dispatch. Scripts may be explicit approved artifacts; they
cannot bypass the normal effect boundary.

## Admission and explicit PLAN

Every admitted computation passes the same freeze/admission function before dispatch.
A direct EXPAND in an already-authorized FLOW is frozen at its resolved input boundary;
PLAN exposes that same frozen computation as a named value for deferred inspection or ACT.
This is one elaboration/dispatch path, not an automatic agent loop hidden behind PLAN.
A future dependent action stays a recipe until the actual input exists.

## Host-authored workflow versus model choice

A host-authored FLOW can schedule many computations. A model-facing control invocation
usually returns one bounded typed proposal or one nominated handle. Its grammar can be:

```gbnf
root ::= "ACT run-a plan=plan-a -> outcome-a\n"
       | "ABANDON reject-a target=attempt-a reason=declined\n"
```

The alternatives are frozen from host state. Both remain proposals until normal admission.
In this particular example ACT also needs the live grant/precondition/lease recheck. A
complete grammatical ACT is not proof its plan remains fresh when the output arrives.

The finite-command grammar generator in `reference/grammar.py` is a small test oracle.
It does not implement all GBNF; the native backend must handle real token/Unicode/recursive
matching and agree with the canonical language/type validators on the admitted forms.

The production parser and read-only CLI are documented in PROGRAM_READER.md.
Syntax support is separate from implemented operation handlers and execution admission.
