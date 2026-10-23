# I01 baseline tables (2026-10-22)

Baseline only: no responsiveness optimization or I16 acceptance claim.
Small profile pilots have weak tail estimates; sample counts are explicit.
Native full flow is POST plus subsequent GET, not browser paint. Cold-start
responses are not prediction throughput. Browser double RAF is a paint
opportunity, not hardware presentation; the current app has no pending state.

| Native workload | Successful samples | POST p50/p95/p99 ms | GET ms | Full flow ms | Errors |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 active; 0 initial ratings | 10 | 131.93/140.02/140.02 | 44.09/44.55/44.55 | 176.06/183.70/183.70 | 0 |
| 1 active; 4 initial ratings | 10 | 131.92/132.37/132.37 | 43.94/44.33/44.33 | 175.88/176.33/176.33 | 0 |
| 1 active; 5 initial ratings | 10 | 1219.58/1308.83/1308.83 | 43.85/45.95/45.95 | 1263.93/1351.77/1351.77 | 0 |
| 1 active; 20 initial ratings | 10 | 3571.91/5008.67/5008.67 | 44.14/46.17/46.17 | 3615.96/5051.99/5051.99 | 0 |
| 1 active; 100 initial ratings | 10 | 14290.10/15925.87/15925.87 | 49.91/53.97/53.97 | 14340.78/15976.39/15976.39 | 0 |
| First new fifth (one sample) | 1 | 1786.74 | 45.17 | 1831.91 | 0 |
| 20 active; 5 initial ratings | 20 | 12594.63/22813.80/24019.84 | 11907.58/21744.47/22875.04 | 24502.22/24857.19/24898.48 | 0 |
| 100 active; 5 initial ratings | 85 | 65659.86/115005.79/119870.43 | 67258.24/114646.33/119432.27 | 132918.10/134557.16/134703.71 | 15 |

| Browser initial / measured ratings | Measured clicks | Click→paint opportunity p50/p95/p99 ms | Fresh result? | Max observed long task ms | Preflights |
| ---: | ---: | ---: | --- | ---: | ---: |
| 0 / 1 | 10 | 193.70/202.40/202.40 | 0/10 | 2962.00 | 2 |
| New rating: 0→2 | 1 | 188.60 | separate transition sample | — | — |
| 100 / 100 | 10 | 15213.40/16450.80/16450.80 | 10/10 | 18586.00 | 15 |
| New rating: 100→101 | 1 | 16073.60 | separate transition sample | — | — |
| 20 / 20 | 10 | 3652.35/3806.70/3806.70 | 10/10 | 6628.00 | 8 |
| New rating: 20→21 | 1 | 4998.90 | separate transition sample | — | — |
| 4 / 4 | 10 | 194.20/197.40/197.40 | 0/10 | 2368.00 | 2 |
| New rating: 4→5 | 1 | 1907.70 | separate transition sample | — | — |
| 5 / 5 | 10 | 1338.80/1394.20/1394.20 | 10/10 | 3501.00 | 5 |
| New rating: 5→6 | 1 | 2118.80 | separate transition sample | — | — |

| Workload | Server stage (monotonic) | Spans | p50/p95/p99 ms |
| --- | --- | ---: | ---: |
| browser/0 ratings | http_dispatch | 10 | 131.56/136.63/136.63 |
| browser/0 ratings | prediction_identity_db | 10 | 42.22/44.82/44.82 |
| browser/0 ratings | push_queue | 10 | 0.01/0.02/0.02 |
| browser/0 ratings | rating_identity_db | 10 | 43.60/45.16/45.16 |
| browser/0 ratings | rating_write_db | 10 | 45.79/47.09/47.09 |
| browser/100 ratings | active_build | 10 | 14922.07/16164.58/16164.58 |
| browser/100 ratings | http_dispatch | 10 | 15104.76/16349.57/16349.57 |
| browser/100 ratings | prediction_identity_db | 10 | 53.42/55.28/55.28 |
| browser/100 ratings | prediction_scan | 10 | 23.89/29.01/29.01 |
| browser/100 ratings | push_queue | 10 | 0.02/0.26/0.26 |
| browser/100 ratings | rank_and_release | 10 | 0.03/0.04/0.04 |
| browser/100 ratings | rating_identity_db | 10 | 53.30/59.16/59.16 |
| browser/100 ratings | rating_write_db | 10 | 44.81/49.97/49.97 |
| browser/20 ratings | active_build | 10 | 3437.18/3596.53/3596.53 |
| browser/20 ratings | http_dispatch | 10 | 3579.84/3738.01/3738.01 |
| browser/20 ratings | prediction_identity_db | 10 | 42.60/43.35/43.35 |
| browser/20 ratings | prediction_scan | 10 | 11.02/13.50/13.50 |
| browser/20 ratings | push_queue | 10 | 0.02/0.04/0.04 |
| browser/20 ratings | rank_and_release | 10 | 0.02/0.02/0.02 |
| browser/20 ratings | rating_identity_db | 10 | 43.35/44.88/44.88 |
| browser/20 ratings | rating_write_db | 10 | 45.54/46.33/46.33 |
| browser/4 ratings | http_dispatch | 10 | 131.40/132.85/132.85 |
| browser/4 ratings | prediction_identity_db | 10 | 42.41/42.91/42.91 |
| browser/4 ratings | push_queue | 10 | 0.02/0.02/0.02 |
| browser/4 ratings | rating_identity_db | 10 | 43.18/44.88/44.88 |
| browser/4 ratings | rating_write_db | 10 | 45.36/45.80/45.80 |
| browser/5 ratings | active_build | 10 | 1130.51/1184.30/1184.30 |
| browser/5 ratings | http_dispatch | 10 | 1272.27/1324.43/1324.43 |
| browser/5 ratings | prediction_identity_db | 10 | 42.50/42.91/42.91 |
| browser/5 ratings | prediction_scan | 10 | 9.50/11.49/11.49 |
| browser/5 ratings | push_queue | 10 | 0.02/0.02/0.02 |
| browser/5 ratings | rank_and_release | 10 | 0.02/0.03/0.03 |
| browser/5 ratings | rating_identity_db | 10 | 42.61/44.77/44.77 |
| browser/5 ratings | rating_write_db | 10 | 45.47/46.10/46.10 |
| native/1 active/0 ratings | cached_get | 10 | 42.88/43.36/43.36 |
| native/1 active/0 ratings | http_dispatch | 10 | 130.57/138.63/138.63 |
| native/1 active/0 ratings | prediction_identity_db | 10 | 42.30/46.47/46.47 |
| native/1 active/0 ratings | push_queue | 10 | 0.01/0.02/0.02 |
| native/1 active/0 ratings | rating_identity_db | 10 | 42.66/46.79/46.79 |
| native/1 active/0 ratings | rating_write_db | 10 | 45.73/45.90/45.90 |
| native/1 active/0 ratings | state_identity_db | 10 | 42.85/43.33/43.33 |
| native/1 active/100 ratings | active_build | 10 | 14114.46/15747.21/15747.21 |
| native/1 active/100 ratings | cached_get | 10 | 47.69/49.91/49.91 |
| native/1 active/100 ratings | http_dispatch | 10 | 14288.80/15924.66/15924.66 |
| native/1 active/100 ratings | prediction_identity_db | 10 | 52.87/55.84/55.84 |
| native/1 active/100 ratings | prediction_scan | 10 | 24.64/33.90/33.90 |
| native/1 active/100 ratings | push_queue | 10 | 0.01/0.01/0.01 |
| native/1 active/100 ratings | rank_and_release | 10 | 0.03/0.09/0.09 |
| native/1 active/100 ratings | rating_identity_db | 10 | 52.31/56.92/56.92 |
| native/1 active/100 ratings | rating_write_db | 10 | 45.30/52.35/52.35 |
| native/1 active/100 ratings | state_identity_db | 10 | 47.13/49.10/49.10 |
| native/1 active/20 ratings | active_build | 10 | 3419.76/4860.23/4860.23 |
| native/1 active/20 ratings | cached_get | 10 | 43.14/45.14/45.14 |
| native/1 active/20 ratings | http_dispatch | 10 | 3570.68/5007.39/5007.39 |
| native/1 active/20 ratings | prediction_identity_db | 10 | 42.54/44.30/44.30 |
| native/1 active/20 ratings | prediction_scan | 10 | 13.19/16.65/16.65 |
| native/1 active/20 ratings | push_queue | 10 | 0.01/0.02/0.02 |
| native/1 active/20 ratings | rank_and_release | 10 | 0.02/0.03/0.03 |
| native/1 active/20 ratings | rating_identity_db | 10 | 42.73/43.32/43.32 |
| native/1 active/20 ratings | rating_write_db | 10 | 45.71/207.82/207.82 |
| native/1 active/20 ratings | state_identity_db | 10 | 43.09/45.10/45.10 |
| native/1 active/4 ratings | cached_get | 10 | 42.64/42.82/42.82 |
| native/1 active/4 ratings | http_dispatch | 10 | 130.54/131.05/131.05 |
| native/1 active/4 ratings | prediction_identity_db | 10 | 42.33/42.53/42.53 |
| native/1 active/4 ratings | push_queue | 10 | 0.01/0.02/0.02 |
| native/1 active/4 ratings | rating_identity_db | 10 | 42.58/42.84/42.84 |
| native/1 active/4 ratings | rating_write_db | 10 | 45.64/45.75/45.75 |
| native/1 active/4 ratings | state_identity_db | 10 | 42.59/42.79/42.79 |
| native/1 active/5 ratings | active_build | 10 | 1071.43/1169.01/1169.01 |
| native/1 active/5 ratings | cached_get | 10 | 42.62/44.50/44.50 |
| native/1 active/5 ratings | http_dispatch | 10 | 1218.33/1307.63/1307.63 |
| native/1 active/5 ratings | prediction_identity_db | 10 | 42.65/44.12/44.12 |
| native/1 active/5 ratings | prediction_scan | 10 | 8.01/10.95/10.95 |
| native/1 active/5 ratings | push_queue | 10 | 0.01/0.02/0.02 |
| native/1 active/5 ratings | rank_and_release | 10 | 0.02/0.03/0.03 |
| native/1 active/5 ratings | rating_identity_db | 10 | 42.76/42.92/42.92 |
| native/1 active/5 ratings | rating_write_db | 10 | 45.63/53.00/53.00 |
| native/1 active/5 ratings | state_identity_db | 10 | 42.59/44.47/44.47 |
| native/100 active/5 ratings | active_build | 85 | 1086.06/1548.22/2032.29 |
| native/100 active/5 ratings | cached_get | 85 | 43.73/44.10/48.33 |
| native/100 active/5 ratings | http_dispatch | 85 | 1231.04/1697.45/2187.26 |
| native/100 active/5 ratings | prediction_identity_db | 85 | 42.64/44.47/45.05 |
| native/100 active/5 ratings | prediction_scan | 85 | 9.38/12.26/16.80 |
| native/100 active/5 ratings | push_queue | 85 | 0.01/0.06/0.83 |
| native/100 active/5 ratings | rank_and_release | 85 | 0.02/0.03/0.06 |
| native/100 active/5 ratings | rating_identity_db | 85 | 42.99/44.72/44.98 |
| native/100 active/5 ratings | rating_write_db | 85 | 45.73/52.85/59.35 |
| native/100 active/5 ratings | state_identity_db | 85 | 43.67/44.05/48.26 |
| native/20 active/5 ratings | active_build | 20 | 1067.93/1114.20/1152.95 |
| native/20 active/5 ratings | cached_get | 20 | 43.65/44.08/44.20 |
| native/20 active/5 ratings | http_dispatch | 20 | 1208.96/1260.98/1299.43 |
| native/20 active/5 ratings | prediction_identity_db | 20 | 42.70/44.25/44.29 |
| native/20 active/5 ratings | prediction_scan | 20 | 8.10/10.77/11.59 |
| native/20 active/5 ratings | push_queue | 20 | 0.01/0.01/0.02 |
| native/20 active/5 ratings | rank_and_release | 20 | 0.02/0.03/0.03 |
| native/20 active/5 ratings | rating_identity_db | 20 | 42.68/44.44/47.01 |
| native/20 active/5 ratings | rating_write_db | 20 | 45.80/52.08/52.27 |
| native/20 active/5 ratings | state_identity_db | 20 | 43.62/44.03/44.16 |

| Runtime benchmark | Briev | C | Ratio | Correctness |
| --- | ---: | ---: | ---: | --- |
| ring_buffer | .0545s | .0800s | .68x | MATCH |
| float_math | .2256s | .0713s | 3.16x | MATCH |
| float_math_nonzero | .3733s | .2101s | 1.77x | MATCH |
| sparse_dispatch | .0390s | .0832s | .46x | MATCH |
| print_loop | .0758s | .0874s | .86x | MATCH |
| nbody_newton | 7.7951s | 6.2034s | 1.25x | MATCH |
| nbody_newton_accel | BUILD-FAIL |  |  | SKIP |
| nbody_sqrt | 2.6551s | 2.9671s | .89x | MATCH |
| nbody_sqrt_idio | 2.5741s | 3.3563s | .76x | MATCH |
| fasta | .2584s | .2483s | 1.04x | MATCH |
| fannkuch_redux | .1046s | .1317s | .79x | MATCH |
| mandelbrot | .7901s | .7199s | 1.09x | MATCH |
| kalman_filter_runtime | .3288s | .1801s | 1.82x | MATCH |
| knucleotide | .2526s | .2420s | 1.04x | MATCH |
| cancel_math | .0367s | .0593s | .61x | MATCH |
| bit_clear | 0s | .0002s | 0x | MATCH |
| queue_drain | .0384s | .0561s | .68x | MATCH |
| queue_drain_sym | .0344s | .0536s | .64x | MATCH |
| queue_drain_idio | 0s | .0544s | 0x | MATCH |
| stack_push_pop | .0401s | .0538s | .74x | MATCH |
| interval_step | .0384s | .0618s | .62x | MATCH |
| telemetry_stream | .3533s | .1983s | 1.78x | MATCH |
| pid_control | .4769s | .3777s | 1.26x | MATCH |
| matrix_pipeline | .7938s | .5756s | 1.37x | MATCH |
| accumulator_flush | .2510s | .1559s | 1.61x | MATCH |
| sweep_sparse | .2879s | .1683s | 1.71x | MATCH |
| sweep_mid | .3080s | .2002s | 1.53x | MATCH |
| sweep_dense | .7220s | .5548s | 1.30x | MATCH |
| sweep_arr | .7617s | .5289s | 1.44x | MATCH |
| series_converge | .0001s | .0001s | 1.00x | MATCH |
| global_lifetime | .0389s | .0554s | .70x | MATCH |
| deep_recursion | 0s | 0s | x | MATCH |
| arena_churn | .0397s | .1013s | .39x | MATCH |
| linked_list | 1.2063s | 1.8010s | .66x | MATCH |
| hash_ops | 1.2245s | 1.5001s | .81x | MATCH |
| hash_ops_idio | .8925s | .8638s | 1.03x | MATCH |
| enemy_swarm | .0969s | .1166s | .83x | MATCH |
| recommender | .0167s | .0140s | 1.19x | MATCH |
| ws_frame | .0244s | .0214s | 1.14x | MATCH |
| bridge_glue | done |  |  | MATCH |
| bridge_multi | done |  |  | PASS |
