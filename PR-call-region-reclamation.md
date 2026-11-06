# Reclaim nonescaping native allocations at proved call boundaries

Ordinary helpers returning allocated strings, enums and objects could leave
unreachable allocations after their caller finished consuming them. Knowing the
destination representation did not establish who owned the container or payload.
For example, `make()` must preserve its returned allocation, while `inspect()`
can reclaim it after every alias has finished:

```briev
defn make() -> Ptr { term Malloc#(32); };
defn inspect() -> Bool {
    let original: Ptr = make();
    let alias: Ptr = original;
    Store#(original,42,8);
    term Load#(alias,8) == 42;
};
```

The frontend now solves allocation-identity, alias, field, raw-memory, return
and call constraints to a fixed point for each candidate invocation. Incoming
storage is borrowed independently of newly allocated instances at the same
allocation site. Enum variants and object fields retain separate identities.
Generic specialization uses the same shared identity/substitution machinery as
LLVM emission. Unknown effects remain conservative; no application helper or
user type name authorizes reclamation.

The hosted Linux x86-64 executable consumer tracks actual malloc results in
private per-thread scope records. It releases records at proved call exits;
explicit free/realloc update those records, including failed growth and tracking
suspension. Static strings and caller result slots never become registered
allocations. Explicit program end drains the remaining active scopes. Existing
arenas, libraries, shared libraries, embedded targets and wasm retain their
existing allocation paths.

Two prerequisites surfaced during verification. Definition liveness omitted
runtime-reflection receivers, making calls under `value.^Length` unavailable to
ownership analysis. Also, attribute group 15 was accidentally inside an escaped
newline comment and emitted no IR. Emit its actual conservative effects, and
reserve every referenced attribute ID when cloning effect groups. Preserve pure
function attributes and quoted values.

Final wasm gates also exposed a duplicated `Malloc#` path emitting i64 handles
for a pointer-width type, and a pointer store guessing width from a generic
type's spelling. Share the existing target-width allocator/provenance helper;
use recorded register representation and casting-graph resolution at stores.
Entry scopes additionally require closed scalar global initializers, and their
graph includes reactor conditions. Unclassified initialization or condition
effects cannot silently enter a body-only ownership proof.

A controlled generated-IR experiment isolated linear stack growth from inlining
TLS-visible region frames into a recursive driver. Keep proved region calls
`noinline`, and conservatively leave recursive functions without region exit
epilogues. Their nonrecursive consuming helpers still reclaim each iteration.
Retire this restriction only with a consumer preserving bounded tail execution.

Validation records and exact commands are in
`docs/plans/2026-11-04-collector-reclamation-closure.md`. Native regressions cover
returned and late-used aliases, caller-held fields, static/borrowed and nested
enum payloads, recursive returns, early exits and bounded repeated calls.
Independent allocator bookkeeping checks O0 and O3/LTO, including allocation
failure, realloc failure and explicit frees through suspended scopes.

The branch is based on upstream main and is independent of PR #61. Applying
the environment expansion change produced byte-identical LLVM IR for the JSON
parse, JSON stringify and rating population fixtures.

CI follow-up corrected two reproducible failures. The bounded execution test
now reads Linux resident pages using stdlib facilities present on main. In a
generated-IR control, bypassing reclamation made the same test fail its growth
threshold. LLVM region lowering now consumes complete multiline signatures
before inserting instructions. The two dynamic payload ABI fixtures compile
at O0 and produce their expected results.

Valgrind also exposed a native UTF-8 allocation sized for fewer than four
encoded bytes, and an owned string returned by the external encoding provider
whose allocation was outside the module. Reserve the complete UTF-8 buffer
and register the provider's fresh result. Raw pointer casts preserve alias
identity. A registered custom encoding override invalidates the default
provider proof.

Local verification passed 3,491 library tests with the full source sweep
delegated to CI, all three native region tests including Valgrind, and both
dynamic payload regressions. All nine external collector memory checks passed
using the app's load-harness stdlib prerequisites. Two independent runs each
emitted 5,000 successful samples at 500 Hz. After warmup RSS held at 380 and
368 pages respectively, with virtual memory constant at 3,989,504 bytes.

Hosted CI on dd949230 passed the JSON parse, JSON stringify, rating population
and Tier-1 corpus tests. The run stopped at the HIR unsupported-expression audit
with 62 expressions against a ceiling of 60. GitHub tested a merge with upstream
db4bad7c. The same upstream commit fails the same audit with the same count on
main. The PR branch on its original base passes the audit at 60. The new
sync-group lowering exposes two plugin intercepts in the existing
mixed_effect_shape fixture.

[PR CI run](https://github.com/Randozart/briev-lang/actions/runs/41827974409)
· [Upstream CI run](https://github.com/Randozart/briev-lang/actions/runs/41827028821)
