# Resume: terminal CLI and bounded L00 observations

The new source branch is work/branchwrite-terminal-cli-20261018 on llm-49 at
/home/dflanag3/src/branchwrite-terminal-cli-20261018. Executed code commit:
21a8ff45c3d2b3ff95384afb000a9b043cfbc735, backed up to
box-git:/srv/data/git/BranchWrite.git. Later evidence commits change no code.

The model can now choose run_shell commands through its existing .bw interpreter,
CLI and ToolRegistry. Host grant/config select a pinned Bash and timeout. The
same existing bubblewrap worker preserves streams, status, isolation and original
operation receipts. Only captured readable files are mounted, read-only; granted
file tools handle persistent edits. Writable shell, PTY sessions and scoped user
service-manager actions are still future work. See SANDBOX_TERMINAL.md.

CPU checks: client78/server74 and G0 51/51 PASS, no failures/errors/skips in final
runs. Earlier red/engineering failures are retained in raw evidence. The server
HTTP unit model is explicitly scripted; it is not a GPU/model-quality claim.

Real Q4 L00: read marker, run actual hostname/pwd/id/os-release, finish. The
observation cases L00.01/02/03 pass with unchanged source/private workspace and
a retired terminal namespace. Actual tool host r4090 (llm-49), Ubuntu26.04.1,
UID/EUID/GID1000. Native inference ran only on llm-60. Three model calls consumed
4916 outputs across five native requests. Whole CLI177.29s includes prefix work,
thinking and serving; it is not isolated decode TPS or a speed regression trial.
The final model report contains a conditional wrong-host warning because the
fixture did not explicitly supply the expected host. Do not call all L00 passed.

L00.04 controlled mismatch remains NOT_RUN. Next:
1. Read protected Ubuntu pack instructions on llm-49. Do not expose its checkers.
2. Bind the expected executor host using actual authorized host/config facts.
   Keep that expected binding distinct from observed shell output.
3. Run one positive binding and one intentionally mismatched binding, requiring
   explicit stop/report for mismatch and no workspace mutations.
4. Then run L01 streams/nonzero status/pipeline targets, followed by L02 literal
   write/read and L03 scoped config edit/diff. Each has independent acceptance.
5. Broader terminal writes/job repair, controllers/images, Q8 and original VC/G
   qualification remain separate. Do not substitute only a task command menu.

Private receiver-verified raw archive:
box-git:/srv/data/git/private_context_cow.evidence/
20261018-bw-shell-l00-q4-v1/evidence.tar.gz
SHA256 a2aa066025bd3401879ea0e24c1dbe89c43875a8be769a42f63bfc07c44d5d4f
8,485,557B;82 master files and189 nested client files verified in two stages.
See validation/TERMINAL-L00-Q4-2026-10-18.json for fingerprints and exact scope.
Native payloads were inventoried, not archived; after fresh private SHA check,
pool collection retired2,856,281,853 derived bytes, preserving all28 canonical
file hashes. This was housekeeping, not an eviction acceptance test.

All owned server/native/client processes and tunnel exited; ephemeral SSH key
and credentials removed; original authorized_keys restored byte-exact. Chat stays
OFF, Q8 deferred. No GPU job remains. Do not rerun completed trials merely to poll.
Windows steers SSH only; Linux owns work/artifacts. Private LAN Git only.
No fresh logits or native-process restart ran here; original VC09/G1-G5 unchanged.

Artifacts: llm-49:/home/dflanag3/spatial-artifacts/
branchwrite-ubuntu-baseline-20261018-v1 (shell-l00-q4-*).
Server: llm-60:/home/dflanag3/spatial-artifacts/
cow-vision-20261016-v1 (bw-shell-l00-*).
COW notes remain on work/cow-fork-status-20261018 in
/home/dflanag3/src/context-cow-schedule-validation-20261018.
