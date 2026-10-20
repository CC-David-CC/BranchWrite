# Resume: bound L00 passed; next L01 output handling

Current BW source: llm-49:/home/dflanag3/src/branchwrite-executor-binding-20261018,
branch work/branchwrite-executor-binding-20261018. Code executed:
be89e1b4f5274f68e2e3bac4e7aaad8a66f2a8a4. Later notes change no production code.
Private Git: box-git:/srv/data/git/BranchWrite.git. COW notes/source remain on
llm-60:/home/dflanag3/src/context-cow-schedule-validation-20261018,
work/cow-fork-status-20261018; inference uses frozen runtime9a289063/profile2370721c.

L00.01-04 PASS in this bounded campaign. Q4 observed actual tool host r4090
(llm-49), Ubuntu26.04.1, UID/EUID/GID1000, cwd and marker. The configured expected
hostname was supplied separately as task context. A deliberately wrong hostname
was rejected by the real CLI before any workflow state or native work. This is
a host admission guarantee, not a model reasoning attempt on a wrong host.
CPU client84/server80 and G0 51/51 passed with no final failures/errors/skips.

Actual Q4 used four model calls/four native requests/980 output tokens and
49.48s whole CLI time. This is not pure decode TPS or an isolated speedup over
the earlier177s differently prompted run. Source/private workspace unchanged,
numeric identities verified through actual shell/proc output, all namespaces
retired. Initial audit mistakenly required full os-release; the model validly
selected the required release fields. That audit error is retained, not a model
failure, and no rerun was needed.

Raw evidence:
box-git:/srv/data/git/private_context_cow.evidence/
20261018-bw-host-bound-l00-q4-v1/evidence.tar.gz
SHA2564f641ac96c12a27fcb1cffa0015c6a170e96aca2192b29fca3da2dba45f11723,
4,527,996B;71 master data files plus204 nested client files independently checked.
Optional native payloads inventoried, not archived. After fresh backup check,
the existing pool retired2,146,900,270 derived bytes;24 canonical files unchanged.
Housekeeping is not an eviction acceptance test. No numerical oracle or native
process restart was part of this target. Original VC09/G1-G5 remain unqualified.

Next:
1. Add explicit raw-artifact identity and UTF-8 replacement/truncation metadata
   to tool feedback. Raw bytes already persist exactly; displayed text currently
   uses replacement decoding without explicit annotation.
2. Test binary bytes and model feedback delivery before live L01. Preserve raw
   stdout/stderr, actual nonzero status, original operations and process retirement.
3. Prepare L01 from the protected Ubuntu pack, one target at a time. Run actual
   streams.sh and both pipeline probes. Check all five L01 obligations, including
   binary data and delivery, without pretending a file-readback verifier itself
   judges terminal semantics. The workload oracle remains protected.
4. Then L02/L03, with affected regressions. Broader terminal writes/job repair,
   images/controllers, Q8 and full certification remain separate.

All owned clients/server/native processes and tunnel exited, ephemeral SSH key
and credentials deleted, original authorized_keys restored byte-exact. GPU idle;
chat stays OFF, Q8 deferred. Windows steers only; Linux owns code/tests/artifacts.
Private LAN Git only. Do not rerun terminal jobs merely to poll.

Artifacts: llm-49:/home/dflanag3/spatial-artifacts/
branchwrite-ubuntu-baseline-20261018-v1/host-bound-l00-q4-* and
executor-binding-tests-v1. Server/raw:
llm-60:/home/dflanag3/spatial-artifacts/cow-vision-20261016-v1/
bw-host-bound-l00-* and bw-executor-binding-*.
