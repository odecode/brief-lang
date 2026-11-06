# Expand environment macros in every expression position

## Problem and example

Environment macros nested in loops, guards, index operands or another macro's
arguments could survive parsed-stage expansion and reach LLVM as unresolved
plugin intercepts. For example:

```briev
foreach index in 0..get_env_int!("COUNT") {
    when get_env_int!("ENABLED") == 1 {
        let value: Int = get_env_int!(get_env!("VALUE_KEY"));
    };
};
```

These expressions should lower to calls to the environment stdlib functions.
The environment plugin maintained its own incomplete AST recursion, omitting
foreach statements, guards, index subscripts and plugin-intercept arguments.

## Change and soundness

Use the existing exhaustive mutable AST visitor in postorder. It visits children
before rewriting the parent, so nested arguments are already expanded when a
macro becomes a call. Preserve receiver-first call argument order, leave
unrelated plugin names intact, and retain the separate direct-constant
evaluation pass. No source syntax, stdlib ownership or allocation policy changes.

Regression tests cover loop bounds, guards, index operands, nested macros,
children of unknown plugins and chained receivers. A native integration fixture
uses runtime environment inputs and checks exact output after computing 21.

## Verification

Native integration passes with LLVM 17 selected on PATH and prints
`nested_env_ok`. Compiler build passes without new warnings. Praetor passes the
tests directory and reports no diagnostics in the changed environment plugin;
17 diagnostics remain in untouched plugin files. Corrected focused unit tests pass 3/3. Final library verification passes 3,441 tests with only the previously delegated conformance sweep excluded. Quick IR determinism passes all three corpus programs. The first unit fixture used invalid
list syntax; it has been corrected to `List<Int>`. An initial native invocation
failed because bare `opt` was absent from PATH; selecting the installed LLVM 17
bin directory resolved that setup issue.

This fix is independent of general allocation provenance and reclamation; it
does not establish leak-free file results or bounded collector memory.
No merge-order dependency is known; validate the clean carve-out against main.
