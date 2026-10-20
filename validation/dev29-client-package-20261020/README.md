# Private BranchWrite dev29 client package

Built the wheel from source commit 5fb74d46772d7005dc0177444610055ba7204842
and installed it into an isolated venv on llm-49:

/home/dflanag3/spatial-artifacts/branchwrite-dev29-package-20261020-v1

The installed CLI exposes build-project-context and context-source-branch under
code, plus context-status. The installed doctor passed file/shell-isolation
smoke checks with inference NOT_RUN. Source-level receipt tests (71) and the
actual local CPU Context COW HTTP suite (7) are documented in
../project-context-receipt-20261020. No Q4/Q8 model test ran, and this package
is not a full-agent certification.
