# Target-width constant globals

2026-10-22. Main-based compiler prerequisite on `codex/wasm-const-width`.

## Evidence and hypothesis

The I02 protocol fixture declares `PROTOCOL_ITEMS: Int` and compares an Int
field against it on wasm32. Its generated LLVM IR loads the constant as i64 and
compares it with i32. The global and read paths use `protocol_llvm_type` and a
hardcoded `load i64`, while ordinary Briev `Int` expressions use the selected
target width. `Int` is i32 on wasm32 and i64 on the native target.

This is a general mismatch between target-independent protocol metadata and the
backend's target-specific representation. The fix uses the backend's existing
`llvm_type` resolver for constant globals, aliases, and reads, preserving the
declared Briev type in the loaded register.

## Verification

Add a wasm32 regression that checks a typed Int constant declaration and read
both use i32. Run the focused LLVM tests, compile the actual I02 WASM fixture,
and run the full library suite against the accepted failure baseline. Build
without new warnings and run directory-scoped Praetor. Update the LLVM backend
architecture and bug log in the same logical compiler change.
