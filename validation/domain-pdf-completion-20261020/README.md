# Combined domain and PDF completion

A successful CAD/Blender inspection previously bypassed the PDF obligations of
ordinary project completion. The same canonical PDF receipt verifier now also
runs for CAD and Blender policies. Every current page must be rendered; source
edits invalidate the previous PDF build until rebuilt and rerendered. Tool
receipts remain the evidence, not a model-supplied reviewed flag.

The corrected old-source baseline fails two rejection tests: an unrendered page
and an actual successful source replacement followed by a fresh CAD inspection.
The changed source passes all 40 focused tests, with zero failures/errors/skips
in 196.960 seconds. Tests use actual isolated CAD STEP measurement/rendering,
Blender/MCP execution and PDF build/reopen/page rendering. No inference was run
in this focused regression; this is not a native G1-G5 qualification.

## Fixture correction retained honestly

The earlier new stale-source fixture used before/after fields with
replace_text_file, which actually takes lines/line_ending/final_newline. PLAN
rejected that malformed action. Since rejected plans produce no executed tool
outcome, checking only returned exit codes missed the absence of the edit. The
diagnostic showed unchanged source and inventory; that earlier 36/37 failure
was not evidence that the updated PDF verifier accepted a successful edit.
The final fixture uses the correct friendly-tool arguments and additionally
asserts the complete executed tool sequence and exact changed source bytes.
Both successful rebuild cases remain acceptance tests; rejection alone is not
sufficient. Original diagnostic/intermediate logs remain in the Linux raw root.

No tolerances, numerical reference equations or registered native tests changed.
