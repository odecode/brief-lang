Ordinary local collection assignment now replaces its binding rather than
inserting the replacement handle as an element. This fixes corrupted list
accumulators such as `values = values + [next]`, which previously printed heap
addresses instead of the intended values.

The new lowering seam uses declared InsertAt metadata and exact type equality.
It applies after existing state/member handling and before the historical
insertion fallback. Explicit arrow insertion and different-type fallback remain
unchanged. No function or Briev type name is recognized by the fix.

The minimal discriminator is scratch/task12_list_rebind.bv: before, two pointer
values; after, 1 and 2. The native regression also covers object replacement
followed by explicit push. Three unit tests cover existing/new local storage and
unchanged fallbacks. See the collection-rebinding plan and backend architecture
documentation for details. Merge this fix before the task-12 server feature.

Verification: compiler build, three focused unit tests, native regression and
task-12 account-map/owner-cache integration gates pass. IR determinism is green.
Full library baseline comparison and Praetor evidence are in the server plan.
