#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Verify completed cargo test --lib output against the exact accepted failure set."""
import argparse
import hashlib
import json
import pathlib
import re


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True, type=pathlib.Path)
    parser.add_argument("--accepted", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    text = args.log.read_text()
    summary = re.search(r"test result: (\w+)\. (\d+) passed; (\d+) failed;.*finished in ([0-9.]+)s", text)
    if not summary:
        raise SystemExit("No completed library result; compilation/interruption is not a passing gate.")
    tail = text[text.rfind("failures:"):]
    observed = set(re.findall(r"^    ([A-Za-z0-9_:]+)$", tail, re.MULTILINE))
    accepted = set(args.accepted.read_text().splitlines())
    evidence = {"passed": int(summary[2]), "failed": int(summary[3]),
                "seconds": float(summary[4]), "expected_failures": sorted(accepted),
                "observed_failures": sorted(observed), "new_failures": sorted(observed - accepted),
                "missing_failures": sorted(accepted - observed),
                "log_sha256": hashlib.sha256(args.log.read_bytes()).hexdigest()}
    args.output.write_text(json.dumps(evidence, indent=2) + "\n")
    if observed != accepted or int(summary[3]) != len(accepted):
        raise SystemExit("Library failures differ from the approved baseline; inspect the evidence JSON.")
    print(f"{summary[2]} passed; exact {len(accepted)} accepted failures; no new names")


if __name__ == "__main__":
    main()
