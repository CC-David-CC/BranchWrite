# Sources and status

Consulted 2026-10-16. These are primary upstream references, not claims about the installed
BranchWrite/COW backend. `master` is moving; pin the actual implementation revision before
porting behavior or issuing native acceptance. No algorithm is named “Adaptive 2” here.

- llama.cpp GBNF guide: https://raw.githubusercontent.com/ggml-org/llama.cpp/master/grammars/README.md
  Supports non-JSON grammars, character/literal syntax and native-token matching distinctions.
- llama.cpp sampler API: https://raw.githubusercontent.com/ggml-org/llama.cpp/master/include/llama.h
  Defines clone/reset/accept interfaces; documents Adaptive-P as a terminal selecting sampler
  and recommends mild truncation, with Min-P as a suggested predecessor.
- llama.cpp sampler implementation: https://raw.githubusercontent.com/ggml-org/llama.cpp/master/src/llama-sampler.cpp
  Primary reference for actual Typical, DynaTemp, XTC, Mirostat, DRY, RNG/state behavior.
- llama.cpp common sampling integration: https://raw.githubusercontent.com/ggml-org/llama.cpp/master/common/sampling.cpp
  Exposes grammar-first versus rejection integration, profile construction and native path
  constraints. This is why BW's own grammar-first order must be a tested contract.
- Adaptive-P upstream change reference (linked by the API):
  https://github.com/ggml-org/llama.cpp/pull/17927

The original uploaded archive and native CLI reference are primary project evidence in
`provenance/`. Its utility test rerun is retained in `validation/source-v020-tests.txt`.
The proposed architecture, DSL, test-time budget policy and local reference oracle are
new design work, not assertions of demonstrated product/runtime behavior.
