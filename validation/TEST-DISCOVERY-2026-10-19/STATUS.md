# Test discovery tooling, 2026-10-19

Candidate, not installed or fully qualified. The real read-only bubblewrap runner now supports package-free test directories and retains package-relative imports. No package marker is inserted and no sandbox flag changes. Empty discovery returns exit 1 with a truthful no-test-cases diagnostic.

Executed on llm-49: five new discovery controls plus seven existing execution controls passed (12/12). Initial red and intermediate evidence retained. The same retained SC18 source, repaired world and independent audit ran without added package markers: original 12 methods fail, repaired 12 pass, independent 13 pass; see raw result receipt.

Outstanding: the old registry assertion requires the historical `Start directory is not importable` diagnostic for a fixture containing no test cases. Its test remains unchanged. The candidate deliberately reports the actual empty-suite failure instead. Broader regression qualification is NOT PASS. A prior 91-method run also lacked browser-executable configuration; that environment issue remains separate. No GPU or installed-client validation is claimed for this ticket.

## Broader follow-up

Executed 92 methods on llm-60: 91 pass, one preserved legacy diagnostic assertion fails, zero skips/errors. Real Chromium capture passed using `/snap/chromium/current/usr/lib/chromium-browser/chrome`. See related-controls-v2.log. This supersedes the earlier missing-browser environment issue, not the retained historical failure. Commit cc0ec63 backed up to private box-git BranchWrite.git on feat/explicit-model-reconciliation-20261019. Candidate not installed.

## Isolated installed dev18

Wheel built from e2999bf on llm-49. Installed into a new venv; 22/22 execution/discovery/status controls passed, zero skips. All 42 installed package modules match wheel bytes. No source checkout on import path; see installed-dev18/module-proof.json. Existing dev17 installation untouched. No fresh GPU run; broader 92-method result remains 91 pass / one retained diagnostic assertion failure. Candidate is not a fully qualified release.
