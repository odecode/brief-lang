# Fix relative code-import path resolution

## Problem and discriminator

A documented relative code import such as
`import "../examples/recommender/udata.bv";` fails before typechecking.
The diagnostic shows that the compiler searches for
`///examples/recommender/udata.bv` instead. A sibling import such as
`import "./value.part.bv";` also loses its directory marker and filename dot.
Bare dotted module names, such as `package.value`, must continue resolving to
`package/value.bv`.

The regression fixtures isolate this distinction: they create an actual parent
module and a sibling module with a dotted filename, then resolve each from a
nested importing file. A separate fixture verifies bare namespace expansion.
The tests are self-contained; the recommender files are not required by this PR.

## Root cause and fix

At `src/import_resolver.rs:986`, code import resolution previously applied
`raw_base.replace('.', "/")` to every extension-stripped specifier before
selecting the relative source directory. That destroyed the `./` and `../`
components which the same resolver explicitly supports.

`code_module_path` (`src/import_resolver.rs:1499`) preserves filesystem-relative
bases and expands dots only for bare module specifiers. Extension selection,
search order, source-directory selection, cycle detection, and import filtering
retain their existing behavior. The distinction is based on path syntax and
applies to all code dialects using this resolution path.

The helper keeps the change out of the already-large resolver control flow.
Existing rationale is retained and the extension-split comment is corrected.
BUGS.md and the import architecture note document the resolved behavior.

## Tests and verification

- `relative_code_imports_preserve_filesystem_components` (line 1873): parent
  path with explicit and implicit extensions, current-directory dotted filename,
  and combined current/parent components.
- `bare_dotted_code_import_still_expands_namespace` (line 1893): bare dotted
  namespace still resolves to its directory-based module.
- Human-run WSL `cargo check`, `cargo test --lib`, and debug `cargo build`:
  all green after the final helper extraction.
- Before helper extraction, the rebuilt compiler checked `udata.bv` successfully
  and compiled the unchanged failing import; the native parser gate printed all
  six checks true. The subsequent extraction preserved the conversion logic.
- Praetor: full src scan reports existing diagnostics. A same-config comparison
  of the original and final resolver reports identical diagnostics after
  normalizing temporary paths and shifted line numbers: no new diagnostics.

## Scope and merge order

Branch `fix/relative-import-paths` is cut from `main` and contains only the
compiler fix, its regression tests, and related documentation. No application
or stdlib feature files and no other compiler-fix branches are included.
This fix has no dependency on the pending pointer-provenance fix. Merge this
PR before resuming the recommender task 10 gate on the feature/integration
branch. The human submits and merges the PR, then the vessel picks up upstream
main according to WORKFLOW.md. Feature work is paused for this handoff.
