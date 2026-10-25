#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Archive the exact-engine gate and its interleaved same-process timings."""
import argparse
import hashlib
import json
import pathlib
import platform
import re
import shutil
import statistics
import subprocess


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(full):
    rows = []
    for line in full.splitlines():
        if not line.startswith("active_profile users="):
            continue
        row = dict(re.findall(r"(\w+)=([^ ]+)", line))
        if row["equivalent"] != "true" or row["ids_match"] != "true":
            raise SystemExit("A reference comparison failed; timings remain provisional.")
        rows.append(row)
    return rows


def summary_row(count, selected):
    if len(selected) != 3:
        raise SystemExit(f"Expected three same-geometry pairs for {count} ratings.")
    reference = statistics.mean(int(row["reference_us"]) for row in selected) / 1000
    candidate = statistics.mean(int(row["view_us"]) for row in selected) / 1000
    error = max(float(row["max_error"]) for row in selected)
    return f"| {count} | 3 | {reference:.3f} | {candidate:.3f} | {reference/candidate:.2f} | {error:.3g} |"


def write_summary(output, metadata, full, reuse):
    groups = {}
    for row in metadata["rows"]:
        if row["owner"] == "2147483000":
            groups.setdefault(int(row["ratings"]), []).append(row)
    lines = ["# I06 exact active-profile engine", "", metadata["method"], "", metadata["limit"], "",
             "| Ratings | Pairs | Reference mean ms | View mean ms | Ratio reference/view | Max score/similarity error |",
             "| ---: | ---: | ---: | ---: | ---: | ---: |"]
    for count in (0, 4, 5, 20, 100):
        lines.append(summary_row(count, groups.get(count, [])))
    lines += ["", "Exact ranked IDs/order and finite catalogue scores passed at every row. Zero/four-rating rows force engine evaluation for reference coverage; the worker API returns cold-start without scoring below five distinct ratings.", "", "```text"]
    lines += [line for line in full.splitlines() if line.startswith(("active_components ", "active_profile_prepare ", "active_scratch_ab "))]
    lines += reuse.splitlines()
    lines += ["```", ""]
    (output / "summary.md").write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", required=True, type=pathlib.Path)
    parser.add_argument("--snapshot", required=True, type=pathlib.Path)
    parser.add_argument("--artifacts", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    root = pathlib.Path(__file__).resolve().parents[2]
    args.output.mkdir(parents=True, exist_ok=False)
    full = (args.artifacts / "full.log").read_text()
    edge = (args.artifacts / "edge.log").read_text()
    reuse = (args.artifacts / "reuse.log").read_text()
    if "active_profile_full_gate=true" not in full or "active_profile_edge_gate=true" not in edge:
        raise SystemExit("Both complete correctness gates must pass before timings are accepted.")
    if "bounded=true" not in reuse:
        raise SystemExit("Repeated evaluation must pass its resident-memory gate.")
    rows = read_rows(full)
    sources = [root / "examples/recommender" / name for name in
               ("active_profile.bv", "prediction_scratch.bv", "server_model.bv", "cf_engine.bv")]
    sources += sorted((root / "tests/fixtures/recommender").glob("active_profile*.bv"))
    sources += [root / "tests/fixtures/recommender/run_active_profile.sh", pathlib.Path(__file__).resolve()]
    metadata = {"commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "machine": platform.uname()._asdict(), "compiler_sha256": digest(args.compiler),
        "snapshot_sha256": digest(args.snapshot), "snapshot_bytes": args.snapshot.stat().st_size,
        "dataset_sha256": digest(root / ".kiro/specs/recommender-app/u.data"),
        "binary_sha256": {name: digest(args.artifacts / name) for name in
                          ("active_profile_gate", "active_profile_full_gate", "active_profile_reuse_gate")},
        "ir_sha256": digest(args.artifacts / "active_profile_full_gate.ll"),
        "clang": subprocess.check_output(["clang", "--version"], text=True).splitlines()[0],
        "source_sha256": {str(path.relative_to(root)): digest(path) for path in sources},
        "lambda": .5, "rows": rows,
        "method": "Single process and immutable snapshot; reference then candidate repeated three times per profile. Timings exclude ranking, include build and full catalogue score scan. One-time base preparation reported separately. No competing builds/tests during timing.",
        "limit": "Three-pair engine microbenchmark, not an I16 browser/load acceptance run."}
    (args.output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    for name in ("edge.log", "full.log", "reuse.log", "edge-build.log", "full-build.log", "reuse-build.log"):
        shutil.copy2(args.artifacts / name, args.output / name)
    write_summary(args.output, metadata, full, reuse)


if __name__ == "__main__":
    main()
