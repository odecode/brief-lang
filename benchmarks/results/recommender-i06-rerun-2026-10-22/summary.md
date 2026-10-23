# I06 exact active-profile engine

Single process and immutable snapshot; reference then candidate repeated three times per profile. Timings exclude ranking, include build and full catalogue score scan. One-time base preparation reported separately. No competing builds/tests during timing.

Three-pair engine microbenchmark, not an I16 browser/load acceptance run.

| Ratings | Pairs | Reference mean ms | View mean ms | Ratio reference/view | Max score/similarity error |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 3 | 72.114 | 10.237 | 7.04 | 0 |
| 4 | 3 | 821.679 | 19.398 | 42.36 | 3.22e-06 |
| 5 | 3 | 926.763 | 19.845 | 46.70 | 6.91e-06 |
| 20 | 3 | 2908.473 | 31.654 | 91.88 | 7.75e-06 |
| 100 | 3 | 12583.773 | 74.060 | 169.91 | 5.72e-06 |

Exact ranked IDs/order and finite catalogue scores passed at every row. Zero/four-rating rows force engine evaluation for reference coverage; the worker API returns cold-start without scoring below five distinct ratings.

```text
active_components ratings=5 copy_us=1176 csr_us=2581 means_us=259 similarity_us=897482 checksum=-149.102036
active_components ratings=100 copy_us=1219 csr_us=2419 means_us=289 similarity_us=12093636 checksum=18.4322014
active_profile_prepare users=943 items=1682 nnz=100000 bytes=3645280 prepare_us=289222
active_scratch_ab pairs=10 allocating_scan_us=198819 reusable_scan_us=181130 equivalent=true
active_profile_reuse before_pages=17376 after_pages=17377 extra_pages=1 bounded=true checksum=286.927704
```
