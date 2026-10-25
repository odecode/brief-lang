# Cache integration: complete runtime harness ledger (2026-10-22)

Baseline: release build before cache integration, based on integration HEAD eb1cd907 with uncommitted task-14 portable lowering prerequisites. This is not a clean-commit controlled compiler baseline. Final: release build with cache integration and final task-14 correctness changes. Both use the repository runtime harness, via an LF-only executor copy in the same directory. All rows are recorded, including failures.

Timings are PROVISIONAL development observations: compiler/test jobs ran concurrently, so these runs do not establish compiler performance regressions or speedups. No cache speedup ratio is inferred from these unrelated compiler kernels. Application same-geometry cold/warm observations and direct-reference checks are in the cache-reuse plan.

The baseline harness reached its last bridge entry, then exited on the existing nested shell CRLF failure. The after run also reached the final bridge entry and exited on the same nested shell CRLF failure. Both runs include the nbody_newton_accel pthread-link failure and bridge_glue Python host segfault; Node is absent in WSL. Accepted environment failures were not repaired.

| Benchmark | Before Briev s | Before C s | Before verdict | After Briev s | After C s | After verdict |
| --- | ---: | ---: | --- | ---: | ---: | --- |
| ring_buffer | .0608 | .0887 | MATCH | .0390 | .0578 | MATCH |
| float_math | .2597 | .1034 | MATCH | .1993 | .0591 | MATCH |
| float_math_nonzero | .4323 | .2334 | MATCH | .3153 | .1855 | MATCH |
| sparse_dispatch | .0420 | .0800 | MATCH | .0342 | .0598 | MATCH |
| print_loop | .0540 | .0833 | MATCH | .0369 | .0586 | MATCH |
| nbody_newton | 11.0452 | 8.0445 | MATCH | 7.2796 | 5.7128 | MATCH |
| nbody_newton_accel | — | — | build failure | — | — | build failure |
| nbody_sqrt | 3.0407 | 3.9513 | MATCH | 2.7186 | 3.1438 | MATCH |
| nbody_sqrt_idio | 3.5580 | 3.9661 | MATCH | 2.6432 | 3.1355 | MATCH |
| fasta | .2670 | .2903 | MATCH | .2051 | .2172 | MATCH |
| fannkuch_redux | .1582 | .1705 | MATCH | .0851 | .1038 | MATCH |
| mandelbrot | .9093 | .8684 | MATCH | .6167 | .6479 | MATCH |
| kalman_filter_runtime | .4035 | .2225 | MATCH | .2696 | .1518 | MATCH |
| knucleotide | .3692 | .3724 | MATCH | .2050 | .2061 | MATCH |
| cancel_math | .0430 | .0738 | MATCH | .0346 | .0491 | MATCH |
| bit_clear | 0 | .0014 | MATCH | .0010 | .0006 | MATCH |
| queue_drain | .0622 | .0717 | MATCH | .0374 | .0482 | MATCH |
| queue_drain_sym | .0454 | .0612 | MATCH | .0327 | .0465 | MATCH |
| queue_drain_idio | 0 | .0601 | MATCH | .0007 | .0459 | MATCH |
| stack_push_pop | .0466 | .0620 | MATCH | .0360 | .0468 | MATCH |
| interval_step | .0448 | .0685 | MATCH | .0333 | .0490 | MATCH |
| telemetry_stream | .3713 | .2198 | MATCH | .3000 | .1748 | MATCH |
| pid_control | .5710 | .4208 | MATCH | .4314 | .3271 | MATCH |
| matrix_pipeline | .8370 | .7419 | MATCH | .6804 | .5000 | MATCH |
| accumulator_flush | .2664 | .1944 | MATCH | .3135 | .1491 | MATCH |
| sweep_sparse | .3249 | .1686 | MATCH | .2539 | .1350 | MATCH |
| sweep_mid | .3666 | .2042 | MATCH | .3737 | .2389 | MATCH |
| sweep_dense | .9523 | .6745 | MATCH | .5846 | .4510 | MATCH |
| sweep_arr | 1.0494 | .6976 | MATCH | .6340 | .4340 | MATCH |
| series_converge | .0015 | .0018 | MATCH | .0007 | .0012 | MATCH |
| global_lifetime | .0488 | .0956 | MATCH | .0735 | .1335 | MATCH |
| deep_recursion | .0012 | .0009 | MATCH | .0010 | .0018 | MATCH |
| arena_churn | .0712 | .1566 | MATCH | .0365 | .0792 | MATCH |
| linked_list | 1.4393 | 2.3340 | MATCH | .8935 | 1.3816 | MATCH |
| hash_ops | 1.8503 | 2.1082 | MATCH | 1.3156 | 1.4367 | MATCH |
| hash_ops_idio | .9942 | .9785 | MATCH | .7737 | .7484 | MATCH |
| enemy_swarm | .1067 | .1242 | MATCH | .0852 | .1042 | MATCH |
| recommender | .0217 | .0185 | MATCH | .0105 | .0140 | MATCH |
| ws_frame | .0257 | .0235 | MATCH | .0232 | .0184 | MATCH |
| bridge_glue | — | — | host Python segfault | — | — | host Python segfault |
| bridge_multi | — | — | Python MATCH; Node absent; shell CRLF failure | — | — | Python MATCH; Node absent; shell CRLF failure |
