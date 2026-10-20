# Client project-context receipt validation

This record covers the private BranchWrite project-context builder and its normal
branchwrite code --build-project-context entrypoint. Context COW remains the
canonical store for branch histories and computational checkpoints. BranchWrite
captures selected source files and completed saved branch histories into an
immutable reference pack and records hashes/tip identities in a durable client
receipt. The coding launch pins that receipt hash.

Both suites passed: 71 BranchWrite CPU tests on llm-49 and 7 local CPU COW HTTP
tests on llm-60. The second suite exercised a real HTTP server and COW store with
a deterministic fake model backend. Neither suite used a GPU or Qwen model.

The crash fixture kills the process after the snapshot directory has been
renamed durably but before the outer source receipt is published; recovery uses
the embedded receipt and does not reread changed project files or a moved branch.
The COW HTTP suite also retains the existing lost-acknowledgment recovery tests
for namespace creation and prefix preparation.

Raw test output is in the two adjacent log files. result.json records commands,
counts, commit fingerprints and limitations. This is client/context assembly
evidence, not a real-model correctness, throughput or full crash certification.
