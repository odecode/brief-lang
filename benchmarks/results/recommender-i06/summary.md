# I06 exact active-profile engine

Single process and immutable snapshot; reference then candidate repeated three times per profile. Timings exclude ranking, include build and full catalogue score scan. One-time base preparation reported separately. No competing builds/tests during timing.

Three-pair engine microbenchmark, not an I16 browser/load acceptance run.

| Ratings | Pairs | Reference mean ms | View mean ms | Ratio reference/view | Max score/similarity error |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 3 | 87.707 | 11.733 | 7.48 | 0 |
| 4 | 3 | 976.748 | 26.841 | 36.39 | 3.34e-06 |
| 5 | 3 | 1137.631 | 23.929 | 47.54 | 6.91e-06 |
| 20 | 3 | 3641.202 | 36.789 | 98.98 | 7.75e-06 |
| 100 | 3 | 16009.255 | 80.321 | 199.32 | 5.72e-06 |

Exact ranked IDs/order and finite catalogue scores passed at every row. Zero/four-rating rows force engine evaluation for reference coverage; the worker API returns cold-start without scoring below five distinct ratings.

```text
active_components ratings=5 copy_us=1570 csr_us=3329 means_us=318 similarity_us=1587747 checksum=-149.102036
active_components ratings=100 copy_us=1555 csr_us=3019 means_us=362 similarity_us=16848026 checksum=18.4322014
active_profile_prepare users=943 items=1682 nnz=100000 bytes=3645280 prepare_us=356129
active_profile_reuse before_pages=17383 after_pages=17384 extra_pages=1 bounded=true checksum=286.927704
```
