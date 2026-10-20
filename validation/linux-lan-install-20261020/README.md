# Fresh Linux client and self-contained server smoke

The first website and the follow-up were typed through a real PTY into the
GitHub-installed client in the owned Ubuntu VM. No local model or server package
was installed in that VM. The client called llm-60 over the LAN.

The server engine was rebuilt from the repository sources. Its setup did reuse
unchanged, previously measured local model-file hash receipts; the model itself
was not downloaded again. Both server/native processes exited before restart.
The same BW session then continued and changed the actual client project files.

The browser audit is independent of the model. Its initial sandbox failures and
temporary scoped AppArmor configuration are recorded; they were not model or
website failures. The extra BW browser-worker isolation path did not pass here.
The passing direct audit used Chromium sandboxing, blocked external requests,
and checked both viewport sizes, heading, button, bold names and overflow.

This is installation and bounded workflow evidence, not full numerical or
security certification. See result.json for exact scope and omissions.
