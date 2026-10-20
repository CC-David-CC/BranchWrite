# BranchWrite dev30 private package evidence

Built and installed ranchwrite==0.1.0.dev30 in an isolated virtual environment on llm-49. The smoke checks cover package installation, command discovery, context/recovery help, and ranchwrite doctor.

The client-side receipt recovery implementation and tests are recorded in [client-context-recovery-20261019](../client-context-recovery-20261019/README.md). That bounded run passed 71 BranchWrite tests and 8 real Context COW HTTP integration tests using the deterministic CPU fixture. The restart scenario proves the client can find and reuse the frozen project-source receipt after interruption between the durable snapshot-directory rename and outer-receipt publication, and can then continue a one-step workflow against the server.

This is evidence for the user-side durable receipt and recovery path. It does not claim native inference, a GPU run, or a full server/native-process restart. Inference and GPU checks were not run for this package build.

esult.json records the source commit, wheel hash and test evidence links. The captured build/install logs and CLI/doctor outputs are stored beside it. The distributable wheel is held in the private box-git evidence area under ranchwrite-dev30-package-20261020-v1/wheel/.
