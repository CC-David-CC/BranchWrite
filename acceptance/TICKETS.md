# Implementation tickets

## R01 — Source and repository audit
Depends on: none. Gate: B0.
Source and repository audit through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: BW-G6-001

## R02 — Canonical types and non-JSON syntax
Depends on: R01. Gate: B1.
Canonical types and non-JSON syntax through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: BW-G0-001, BW-G0-004, BW-G0-005, BW-G0-006, BW-G0-016, BW-G0-019, BW-G0-034, BW-G0-039, BW3-LANG-001, BW3-LANG-002, BW3-LANG-003, BW3-LANG-004, BW3-LANG-005, BW3-LANG-006, BW3-LANG-007, BW3-LANG-008, BW3-LANG-009, BW3-LANG-010, BW3-LANG-011, BW3-LANG-012

## R03 — One ledger and canonical storage boundaries
Depends on: R02. Gate: B1.
One ledger and canonical storage boundaries through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: BW3-TYPE-001, BW3-TYPE-002, BW3-TYPE-003, BW3-TYPE-004, BW3-TYPE-005, BW3-TYPE-006, BW3-TYPE-007, BW3-TYPE-008, BW3-TYPE-009, BW3-TYPE-010, BW3-TYPE-011, BW3-TYPE-012

## R04 — Actual native control and receipt discovery
Depends on: R01. Gate: B0.
Actual native control and receipt discovery through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: integration of dependency contracts

## R05 — Typed frames, waits and return reducer
Depends on: R02, R03. Gate: B1.
Typed frames, waits and return reducer through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: BW-G0-018, BW-G0-021, BW-G0-023, BW-G0-024, BW-G0-025, BW-G0-027, BW-G0-028, BW-G0-029, BW-G0-030, BW-G3-014, BW-G3-015, BW-G6-033, BW-G4-016, BW-G4-017, BW-G5-018, BW-G6-035, BW-G6-038, BW-G6-041

## R06 — Type-derived and state-specialized grammars
Depends on: R02, R04. Gate: B2.
Type-derived and state-specialized grammars through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: integration of dependency contracts

## R07 — Native decoder-state transaction contract
Depends on: R02, R04. Gate: B2.
Native decoder-state transaction contract through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: integration of dependency contracts

## R08 — Exact relevant-state freeze and grant checks
Depends on: R02, R03. Gate: B1.
Exact relevant-state freeze and grant checks through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: BW-G0-002, BW-G0-007, BW-G0-008, BW-G0-009, BW-G0-010, BW-G0-011, BW-G0-012, BW-G0-013, BW-G0-014, BW-G0-015, BW-G0-017, BW-G0-020, BW-G0-022, BW-G0-026, BW-G0-031, BW-G0-032, BW3-PLAN-001, BW3-PLAN-002, BW3-PLAN-003, BW3-PLAN-004, BW3-PLAN-005, BW3-PLAN-006, BW3-PLAN-007, BW3-PLAN-008, BW3-PLAN-009, BW3-PLAN-010, BW3-PLAN-011, BW3-PLAN-012

## R09 — Enforced world and effect boundary
Depends on: R01, R08. Gate: B3.
Enforced world and effect boundary through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: BW-G2-001, BW-G2-002, BW-G2-003, BW-G2-004, BW-G2-005, BW-G2-006, BW-G2-007, BW-G2-008, BW-G2-009, BW-G2-010, BW-G2-011, BW-G2-012, BW-G2-013, BW-G2-014, BW-G2-015, BW-G2-017, BW-G2-018, BW-G2-019, BW-G2-022, BW-G2-023, BW-G2-024, BW-G2-025, BW-G2-026, BW-G2-027, BW-G2-028, BW-G2-029

## R10 — Native grammar-first greedy generation
Depends on: R05, R06, R07. Gate: B2.
Native grammar-first greedy generation through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: BW-G1-001, BW-G1-002, BW-G1-004, BW-G1-005, BW-G1-006, BW-G1-007, BW-G1-008, BW-G1-009, BW-G1-012, BW-G1-013, BW-G1-014, BW-G1-016, BW-G1-017, BW-G1-018, BW-G1-019, BW-G1-020, BW-G1-021, BW-G1-022, BW-G1-023, BW-G1-024, BW-G1-025, BW-G1-026, BW-G1-030, BW-G1-031, BW-G1-032, BW-G1-033, BW-G1-034, BW-G1-035, BW-G1-036, BW-G1-037, BW-G1-038, BW-G1-039, BW-G1-040, BW-G1-041, BW-G1-042, BW-G1-043, BW-G1-044, BW-G1-045, BW-G1-046

## R11 — Qualify existing DRY and Min-P baseline
Depends on: R07, R10. Gate: B2.
Qualify existing DRY and Min-P baseline through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: integration of dependency contracts

## R12 — Typed model/tool request and return
Depends on: R05, R08, R09, R10. Gate: B3.
Typed model/tool request and return through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: integration of dependency contracts

## R13 — Headline, status, summary and final invocations
Depends on: R05, R10. Gate: B3.
Headline, status, summary and final invocations through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: BW-G0-035, BW-G0-036, BW-G0-037, BW-G0-038, BW-G1-027, BW-G1-028, BW-G1-029, BW-G6-027, BW-G6-032, BW-G6-034, BW-G6-040, BW3-FEATURE-001, BW3-FEATURE-002, BW3-FEATURE-003, BW3-FEATURE-004, BW3-FEATURE-005, BW3-FEATURE-006, BW3-FEATURE-007, BW3-FEATURE-008

## R14 — First real nested session and return-boundary restart
Depends on: R03, R11, R12, R13, R35. Gate: B4.
First real nested session and return-boundary restart through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: BW-G6-004, BW-G6-026, BW-G6-036

## R15 — Independent native matcher fork and partial continuation
Depends on: R07, R10. Gate: B2.
Independent native matcher fork and partial continuation through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: BW3-GRAM-001, BW3-GRAM-002, BW3-GRAM-003, BW3-GRAM-004, BW3-GRAM-005, BW3-GRAM-006, BW3-GRAM-007, BW3-GRAM-008, BW3-GRAM-009, BW3-GRAM-010, BW3-GRAM-011, BW3-GRAM-012, BW3-GRAM-013, BW3-GRAM-014

## R16 — Versioned RNG and feedback checkpoint lifecycle
Depends on: R07, R15. Gate: B2.
Versioned RNG and feedback checkpoint lifecycle through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: BW3-SAMPLE-001, BW3-SAMPLE-002, BW3-SAMPLE-003, BW3-SAMPLE-004, BW3-SAMPLE-005, BW3-SAMPLE-006, BW3-SAMPLE-007, BW3-SAMPLE-008, BW3-SAMPLE-009, BW3-SAMPLE-010, BW3-SAMPLE-011, BW3-SAMPLE-012, BW3-SAMPLE-013, BW3-SAMPLE-014, BW3-SAMPLE-015, BW3-SAMPLE-016, BW3-SAMPLE-017, BW3-SAMPLE-018

## R17 — DynaTemp native law and edge cases
Depends on: R10, R16. Gate: B5.
DynaTemp native law and edge cases through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: integration of dependency contracts

## R18 — Locally Typical native law and edge cases
Depends on: R10, R16. Gate: B5.
Locally Typical native law and edge cases through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: integration of dependency contracts

## R19 — XTC stochastic exclusion and draw isolation
Depends on: R10, R16. Gate: B5.
XTC stochastic exclusion and draw isolation through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: integration of dependency contracts

## R20 — Mirostat 2 selector law and state
Depends on: R10, R16. Gate: B5.
Mirostat 2 selector law and state through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: integration of dependency contracts

## R21 — Adaptive-P selector law and state
Depends on: R10, R16. Gate: B5.
Adaptive-P selector law and state through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: integration of dependency contracts

## R22 — Parallel model expansion and explicit seed splits
Depends on: R14, R15, R16, R28. Gate: B4.
Parallel model expansion and explicit seed splits through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: integration of dependency contracts

## R23 — Actually overlapping isolated ACT computations
Depends on: R09, R12, R14, R28. Gate: B4.
Actually overlapping isolated ACT computations through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: BW-G4-001, BW-G4-002, BW-G4-003, BW-G4-004, BW-G4-005, BW-G4-006, BW-G4-009, BW-G4-010, BW-G4-011, BW-G4-012, BW-G4-013, BW-G4-014, BW-G4-018, BW3-WORLD-001, BW3-WORLD-002, BW3-WORLD-003, BW3-WORLD-004, BW3-WORLD-005, BW3-WORLD-006, BW3-WORLD-007, BW3-WORLD-008, BW3-WORLD-009, BW3-WORLD-010, BW3-WORLD-011, BW3-WORLD-012

## R24 — Source-bound challenge, compare and selection
Depends on: R05, R08, R12. Gate: B4.
Source-bound challenge, compare and selection through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: BW3-OPS-001, BW3-OPS-002, BW3-OPS-003, BW3-OPS-004, BW3-OPS-005, BW3-OPS-006, BW3-OPS-007, BW3-OPS-008, BW3-OPS-009, BW3-OPS-010, BW3-OPS-011, BW3-OPS-012

## R25 — Complement composition and fresh integration verification
Depends on: R23, R24. Gate: B6.
Complement composition and fresh integration verification through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: integration of dependency contracts

## R26 — Guarded publication and outcome reconciliation
Depends on: R03, R09, R25. Gate: B6.
Guarded publication and outcome reconciliation through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: BW-G3-001, BW-G2-016, BW-G5-001, BW-G5-003, BW-G5-004, BW-G4-007, BW-G4-008, BW-G4-015, BW-G3-009, BW-G5-017, BW-G6-008

## R27 — Native/effect fault and recovery campaigns
Depends on: R14, R16, R23, R26. Gate: B6.
Native/effect fault and recovery campaigns through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: BW-G3-002, BW-G3-003, BW-G3-004, BW-G5-002, BW-G3-005, BW-G3-006, BW-G3-007, BW-G3-008, BW-G3-010, BW-G3-011, BW-G5-005, BW-G5-006, BW-G5-007, BW-G5-011, BW-G5-012, BW-G5-013, BW-G5-015, BW-G5-016, BW-G3-012, BW-G3-013, BW-G3-017, BW-G5-019, BW3-RESTORE-001, BW3-RESTORE-002, BW3-RESTORE-003, BW3-RESTORE-004, BW3-RESTORE-005, BW3-RESTORE-006, BW3-RESTORE-007, BW3-RESTORE-008, BW3-RESTORE-009, BW3-RESTORE-010, BW3-RESTORE-011, BW3-RESTORE-012

## R28 — Shared budgets, leases and dispatch accounting
Depends on: R05, R08. Gate: B3.
Shared budgets, leases and dispatch accounting through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: BW-G1-003, BW-G0-003, BW-G1-010, BW-G1-011, BW-G1-015, BW-G5-008, BW-G5-009, BW-G5-010, BW-G5-014, BW-G0-033, BW-G3-016, BW-G6-030, BW-G5-020

## R29 — Read-only views and one bounded step/run kernel
Depends on: R05, R13. Gate: B4.
Read-only views and one bounded step/run kernel through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: BW-G6-002, BW-G6-003, BW-G6-005, BW-G6-006, BW-G6-007, BW-G6-009, BW-G6-010, BW-G6-011, BW-G6-012, BW-G6-013, BW-G6-014, BW-G6-015, BW-G6-016, BW-G6-017, BW-G6-018, BW-G6-022, BW-G6-023, BW-G6-024, BW-G6-025, BW-G6-028, BW-G6-029, BW-G6-031, BW-G6-037, BW-G6-039, BW-G6-042

## R30 — Fair test-time-compute baseline campaign
Depends on: R11, R22, R23, R24, R28. Gate: B7.
Fair test-time-compute baseline campaign through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: BW3-COMPUTE-001, BW3-COMPUTE-002, BW3-COMPUTE-003, BW3-COMPUTE-004, BW3-COMPUTE-005, BW3-COMPUTE-006, BW3-COMPUTE-007, BW3-COMPUTE-008, BW3-COMPUTE-009, BW3-COMPUTE-010, BW3-COMPUTE-011, BW3-COMPUTE-012

## R31 — One/two-service and platform qualification
Depends on: R09, R27. Gate: B7.
One/two-service and platform qualification through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: BW-G6-019, BW-G6-020

## R32 — Baseline end-to-end product release evidence
Depends on: R26, R27, R29, R30, R31. Gate: B7.
Baseline end-to-end product release evidence through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: integration of dependency contracts

## R33 — Advanced profile integration and accepted-control receipts
Depends on: R17, R18, R19, R20, R21, R30. Gate: B7.
Advanced profile integration and accepted-control receipts through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: integration of dependency contracts

## R34 — Conditional constrained MTP qualification
Depends on: R16, R33. Gate: B8.
Conditional constrained MTP qualification through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: BW3-MTP-001, BW3-MTP-002, BW3-MTP-003, BW3-MTP-004

## R35 — Port fixture vectors and preserve distinguishing mutants
Depends on: R02. Gate: B1.
Port fixture vectors and preserve distinguishing mutants through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: BW-G2-020, BW-G2-021, BW-G6-021

## R36 — Grammar cost, cache reuse and decode telemetry
Depends on: R15, R28. Gate: B5.
Grammar cost, cache reuse and decode telemetry through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: integration of dependency contracts

## R37 — Numerical, statistical and unreachable-target tests
Depends on: R17, R18, R19, R20, R21, R36. Gate: B7.
Numerical, statistical and unreachable-target tests through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: integration of dependency contracts

## R38 — Adversarial scope and publication audit
Depends on: R09, R12, R26. Gate: B7.
Adversarial scope and publication audit through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: integration of dependency contracts

## R39 — Full inherited acceptance regression campaign
Depends on: R01, R32. Gate: B7.
Full inherited acceptance regression campaign through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: integration of dependency contracts

## R40 — Final enabled-capability report and reproducible release
Depends on: R32, R33, R37, R38, R39. Gate: B8.
Final enabled-capability report and reproducible release through the single production interpreter/native boundary, with distinguishing tests and retained evidence.
Primary cases: integration of dependency contracts
