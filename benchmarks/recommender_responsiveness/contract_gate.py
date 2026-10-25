#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Build and run I01/I02 native contracts and build their actual WASM fixture."""
import argparse
import hashlib
import json
import os
import pathlib
import subprocess


def run_fixture(paths, environment, name, log):
    root, compiler, output = paths
    destination = output / name
    fixture = root / "tests/fixtures/recommender" / (name + ".bv")
    subprocess.run([str(compiler), "build", str(fixture), "--out", str(destination)],
                   cwd=root, env=environment, stdout=log, stderr=subprocess.STDOUT, check=True)
    variants = ("0", "1") if name == "responsiveness_trace_gate" else ("0",)
    for trace in variants:
        log.write(f"RUN {name} trace={trace}\n")
        result = subprocess.run([str(destination / name)], cwd=root,
                                env={**environment, "RECOMMENDER_TRACE": trace},
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=120)
        log.write(result.stdout)
        result.check_returncode()
        if name == "responsiveness_print_gate":
            assert result.stdout == "nested-print=0\nnested-print=1\n", result.stdout


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_manifest(root, compiler, output):
    fixtures = root / "tests/fixtures/recommender"
    inputs = sorted((root / "examples/recommender").glob("protocol*.bv"))
    inputs.extend((root / "examples/recommender").glob("worker*.bv"))
    inputs.append(root / "examples/recommender/admission_contract.bv")
    inputs.extend(path for path in (root / "lib/std").rglob("*.bv"))
    inputs.extend(fixtures / name for name in (
        "protocol_contract_checks.bv", "worker_contract_checks.bv",
        "responsiveness_contract_web.rbv", "responsiveness_trace_gate.bv",
        "responsiveness_contract_gate.bv", "responsiveness_frame_gate.bv",
        "responsiveness_print_gate.bv"))
    inputs.extend((root / "benchmarks/recommender_responsiveness" / name for name in (
        "contract_gate.py", "contract_browser.mjs")))
    inputs = sorted(set(inputs))
    web_files = sorted(path for path in (output / "web").iterdir() if path.is_file())
    manifest = {
        "compiler": str(compiler), "compiler_sha256": digest(compiler),
        "inputs": {str(path.relative_to(root)): digest(path) for path in inputs},
        "artifacts": {path.name: digest(path) for path in web_files},
        "gate_log_sha256": digest(output / "gate.log"),
    }
    (output / "contract_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    root = pathlib.Path(__file__).resolve().parents[2]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    compiler = args.compiler.resolve(strict=True)
    environment = {**os.environ, "PATH": "/usr/lib/llvm-17/bin:" + os.environ["PATH"]}
    fixtures = root / "tests/fixtures/recommender"
    with (output / "gate.log").open("w", buffering=1) as log:
        for name in ("responsiveness_trace_gate", "responsiveness_contract_gate", "responsiveness_frame_gate", "responsiveness_print_gate"):
            run_fixture((root, compiler, output), environment, name, log)
        subprocess.run([str(compiler), "build", str(fixtures / "responsiveness_contract_web.rbv"),
                        "--split", "--out", str(output / "web")], cwd=root, env=environment,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    write_manifest(root, compiler, output)
    print(output / "gate.log")


if __name__ == "__main__":
    main()
