# I02 contract verification

The I02 gate log records native trace, protocol, worker, framing and nested-print
fixture results, followed by compilation of the real `.rbv` contract page to
WASM. `contract-manifest.json` records compiler, source, generated artifact and
log hashes. `wasm-browser.json` records the headless Chrome run; both canonical
epoch values passed in the generated Briev page with no page errors.

The checked-in driver reproduces the gate from the repository root:

```bash
env PATH=/usr/lib/llvm-17/bin:/usr/bin:/bin python3 \
  benchmarks/recommender_responsiveness/contract_gate.py \
  --compiler ~/briev-target/debug/brievc --output /tmp/recommender-contract-v1
```

Serve the resulting `web/` directory and run
`benchmarks/recommender_responsiveness/contract_browser.mjs` against its
`responsiveness_contract_web.html`. The page runs the protocol checks in Briev;
Chrome only supplies the browser WASM host.
