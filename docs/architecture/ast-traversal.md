# AST traversal contracts

`ast::visit` provides read-only preorder traversal; `ast::visit_mut` provides
mutable postorder traversal. Both cover executable expression payloads in
statements, contracts, patterns, derivations and behavioral members. Their
exhaustive matches intentionally make a new AST variant a compile error until
both traversal modes classify it. Type-only, foreign-text and declarative data
payloads are not executable expressions.

Mutable callbacks run once per original expression, after its children, in
source order. A replacement is not traversed again. Rewriters must therefore
return already-lowered replacements whose children were processed before the
parent replacement. Keep traversal separate from each pass's semantic callback.
The read/mutable coverage comparison and postorder mutation tests pin these
contracts; add representative new payloads to those tests as the AST evolves.

2026-10-22: the print plugin migrated from partial private walkers after a print
inside a foreach/guard body reached LLVM unresolved. Expansion now covers all
visited positions, including nested receiver/argument macros and previously
skipped operands/containers. Unknown plugin names remain for their owning pass;
their children are still visited. The first expansion error is returned, never
converted into a successful partial program. Formatting stays type-independent;
Print# performs typed dispatch. The obsolete annotation map did not participate
in dispatch and was removed. Retire this traversal only into equivalent shared
AST machinery, never another per-plugin subset.
