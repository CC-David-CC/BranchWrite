# Captured page resources

A page may load local images, CSS, JavaScript and fonts from captured immutable
bytes. The browser never receives a live workspace directory.

The host's grant.asset_paths is an explicit list, at most64 entries, each also
in read_paths. It supplies resources for the registered browser tools. The model
uses the existing read/edit/capture/interact calls; it does not choose paths
outside its grants or copy checksums. Each file must pass the existing private,
regular,no-follow reader. Files are at most4MiB each and16MiB total.

PLAN binds the HTML and every resource preimage. ACT checks those same values
before the browser starts. Exact resource bytes enter the existing RuntimeLog
artifact store,with hashes in the tool receipt; this is not another history.
Canonical nested document URLs retain relative resource resolution. Only those
captured URLs are served; missing/external resources,navigation,WebSockets,
traversal/query aliases and duplicate paths reject. Supported extensions are
PNG/JPEG/WebP/GIF/SVG,CSS,JS,WOFF/WOFF2 and text. Additional HTML documents and
navigation are not supported. Unicode and spaces have one encoded URL identity.

The worker checks closed memfd framing,lengths,SHA256 and media type before
launch. Both Bubblewrap and Chromium sandboxes remain enabled. No host home,
credentials,service socket or candidate directory is mounted. Source/runtime
hashes and the asset grant contribute to tool identity; changed registries are
not silently substituted into prior plans. Use original pinned code to inspect
older runs and a new workflow for new code.

Completion requires actual current HTML readback,an admitted complete-bundle
capture and the matching resource artifacts. Changing resource bytes invalidates
the picture even if rendered pixels are identical. Inspection replays the
model's initial picture,then runs unchanged protected checks separately; its
post-click picture is retained separately. Without checker actions,the protected
picture must still match exactly. Interactive completion replays the actual
source/assets/action recipe and checks its PNG/text before independent checks.

After launcher exit,the host observes namespace retirement for at most0.5s.
It succeeds only when actual members are absent. Persistent members still reject
and include PID diagnostics. This allows bounded kernel cleanup,not surviving
browser processes. Original timeout and output limits remain.

265 selected methods pass:249 client/browser on llm-49 and16 server CPU on llm-60.
The earlier246-method run had one namespace-retirement error;retain it.
Three deterministic retirement tests and20 repeats of that exact actual-browser
method pass,then all249 passed. One unknown-target negative input changed from
newly supported H08 to unregistered H99;its assertion expressions are unchanged.
Protected checkers,equations and numerical tolerances were not edited.

H08's direct/checker/scripted CLI tests pass,but the autonomous Q4 trial is still
UNRUN at this checkpoint. No numerical or GPU claim follows from CPU FlowModel
peers. See validation/BROWSER-ASSET-CONNECTION-2026-10-18.json for exact IDs and
evidence. H00-H07 remain8/13. Full VC09/G1-G5 and Q8 remain outstanding.
Keep chat OFF,Windows steering only and private LAN publication.

## Executed autonomous H08 follow-up

The real llm-49 CLI/Q4 llm-60 workflow passed in105.77s with actual source edit,
two model image deliveries,real control interaction,full-resource replay and
unchanged independent protected checks. Marker pixels were present in the actual
model PNG,not merely an image element. Native history contained600 image rows;
completed offline reopen passed. All owned processes exited and credentials were
removed. See validation/AUTONOMOUS-H08-Q4-2026-10-18.json. H00-H08 are9/13;this
does not qualify numerical/restart/VC/G/Q8 requirements. The explicit per-run
DRY-off sampler does not change the owner-selected global default.
