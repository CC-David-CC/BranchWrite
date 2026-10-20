# Initial standard-parts environment check

The four new tests failed first because bd_warehouse was absent (3 failures, 1 metadata error). Installing pinned bd-warehouse 0.4.0, without changing build123d 0.13.0, made all four pass. Copy-mode installation preserved runtime isolation; no regular CAD runtime files have shared hard links. uv pip check found all 66 packages compatible.

The full CAD module rerun is in cad-regressions.json, with actual executed IDs, failures and skips. setup-check-stdout.json records measured reopened screw and matching-hole geometry. The named 35,651-byte screw export is retained at the Linux artifact path in summary.json. This is CPU setup and isolation evidence; it makes no model or cumulative gate claim. Prior standalone geometry checkers, equations and tolerances were unchanged.

Run the initial setup in SPATIAL-CREATION-GUIDE.md. Reusable smoke checker: tools/check_cad_environment.py. Example: examples/cad/m4_socket_head_screw.py. New tests: tests/test_cad_warehouse.py. Use the dedicated CAD Python, not the lightweight BW client interpreter.
