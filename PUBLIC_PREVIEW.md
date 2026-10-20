# Linux LAN preview: current state

See CURRENT_STATE.md and docs/LINUX-QUICKSTART.md. The recommended client tag is
lan-preview-2026-10-20.1; the server source tag is lan-preview-2026-10-20.
The source-built COW service is now on llm-60:18099. Older notes saying 8099 was
restored and 18099 stopped are historical and have been archived.

The fresh client/server website and restart/follow-up smoke passed, along with
four independent browser viewport checks and 28 focused CPU startup tests. Exact
versions, timing, initial failures and omissions are in
validation/linux-lan-install-20261020. No new full numerical or G1-G5
qualification was obtained. The standalone-agent goal remains incomplete.

BW owns the user/tool/file workflow; COW owns model histories and checkpoints;
Strata runs inference; the acceptance harness checks actual effects. A .bw file
is a workflow recipe, not a model-state dump. Ordinary chat stays off, Q8 is
deferred, and the separate Strata-head upgrade has not started.
