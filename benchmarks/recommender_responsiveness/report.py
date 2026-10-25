#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Summarize retained I01 artifacts without mixing clock domains or cold results."""
import argparse
import collections
import json
import math
import pathlib
import re
import statistics


def quantiles(values):
    values = sorted(values)
    if not values:
        return "—"
    return "/".join(f"{value:.2f}" for value in (
        statistics.median(values), values[math.ceil(.95 * len(values))-1],
        values[math.ceil(.99 * len(values))-1]))


def native_rows(data):
    groups = collections.defaultdict(list)
    for row in data["rows"]:
        groups[row["initial_ratings"]].append(row)
    lines = []
    for count, rows in sorted(groups.items()):
        label = f"{data['concurrency']} active; {count} initial ratings"
        values = [quantiles([row[key] for row in rows]) for key in ("post_ms", "get_ms", "flow_ms")]
        lines.append(f"| {label} | {len(rows)} | " + " | ".join(values) + f" | {len(data.get('errors', []))} |")
    if data.get("first_fifth"):
        row = data["first_fifth"]
        lines.append(f"| First new fifth (one sample) | 1 | {row['post_ms']:.2f} | {row['get_ms']:.2f} | {row['flow_ms']:.2f} | 0 |")
    return lines


def native_table(paths):
    lines = ["| Native workload | Successful samples | POST p50/p95/p99 ms | GET ms | Full flow ms | Errors |",
             "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for path in paths:
        lines.extend(native_rows(json.loads(path.read_text())))
    return lines


def measured_clicks(data):
    clicks = [row for row in data["evidence"] if row["stage"] == "click"]
    if data.get("new_rating_samples"):
        return [row for row in clicks if row.get("purpose") == "measured"]
    return clicks[data["warmups"]:]


def browser_rows(data):
    records = data["evidence"]
    clicks = measured_clicks(data)
    latencies, counts, fresh = [], set(), 0
    for click in clicks:
        events = [row for row in records if row["operation"] == click["operation"]]
        paint = next(row for row in events if row["stage"] == "paint_opportunity")
        latencies.append(paint["ms"] - click["ms"])
        counts.add(paint.get("rating_count", len(re.findall(r"Movie \d+:", paint["ratings"]))))
        fresh += any(row["stage"] == "live_receive" and not row.get("cold_start", False) for row in events)
    tasks = [row["duration"] for row in records if row["stage"] == "long_task"]
    preflights = sum(row.get("method") == "OPTIONS" for row in data["protocol"])
    actual = ",".join(str(count) for count in sorted(counts))
    lines = [f"| {data['initial']} / {actual} | {len(clicks)} | {quantiles(latencies)} | {fresh}/{len(clicks)} | {max(tasks, default=0):.2f} | {preflights} |"]
    for click in (row for row in records if row["stage"] == "click" and row.get("purpose") == "new_rating"):
        paint = next(row for row in records if row["operation"] == click["operation"] and row["stage"] == "paint_opportunity")
        lines.append(f"| New rating: {data['initial']}→{paint['rating_count']} | 1 | {paint['ms']-click['ms']:.2f} | separate transition sample | — | — |")
    return lines


def browser_table(paths):
    lines = ["| Browser initial / measured ratings | Measured clicks | Click→paint opportunity p50/p95/p99 ms | Fresh result? | Max observed long task ms | Preflights |",
             "| ---: | ---: | ---: | --- | ---: | ---: |"]
    for path in paths:
        lines.extend(browser_rows(json.loads(path.read_text())))
    return lines


def native_operations(data):
    return {row["operation"]: f"native/{data['concurrency']} active/{row['initial_ratings']} ratings" for row in data["rows"]}


def browser_operations(data):
    return {row["operation"]: f"browser/{data['initial']} ratings" for row in measured_clicks(data)}


def trace_span(line, pattern):
    found = pattern.fullmatch(line)
    if not line.startswith("TRACE "):
        return found
    if not found or int(found[3]) < 0 or int(found[4]) < int(found[3]):
        raise ValueError("Invalid monotonic trace: " + line)
    return found


def stage_table(path, native_paths, browser_paths):
    operations = {}
    for source in native_paths:
        operations.update(native_operations(json.loads(source.read_text())))
    for source in browser_paths:
        operations.update(browser_operations(json.loads(source.read_text())))
    groups = collections.defaultdict(list)
    pattern = re.compile(r"TRACE op=(\S*) stage=(\S+) start_us=(-?\d+) end_us=(-?\d+)")
    for line in path.read_text().splitlines():
        found = trace_span(line, pattern)
        if not found or found[1] not in operations:
            continue
        groups[(operations[found[1]], found[2])].append((int(found[4])-int(found[3])) / 1000)
    lines = ["| Workload | Server stage (monotonic) | Spans | p50/p95/p99 ms |", "| --- | --- | ---: | ---: |"]
    lines.extend(f"| {workload} | {stage} | {len(values)} | {quantiles(values)} |"
                 for (workload, stage), values in sorted(groups.items()))
    return lines


def runtime_table(path):
    lines = ["| Runtime benchmark | Briev | C | Ratio | Correctness |", "| --- | ---: | ---: | ---: | --- |"]
    for line in path.read_text().splitlines():
        if not line.startswith("║"):
            continue
        fields = [field.strip() for field in line.split("║")[1:-1]]
        if len(fields) == 6 and fields[0] != "Benchmark":
            lines.append("| " + " | ".join(fields[:4] + fields[5:]) + " |")
    return lines


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=pathlib.Path, required=True)
    parser.add_argument("--native", type=pathlib.Path, nargs="+", required=True)
    parser.add_argument("--browser", type=pathlib.Path, nargs="+", required=True)
    parser.add_argument("--server-log", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    lines = ["# I01 baseline tables (2026-10-22)", "",
        "Baseline only: no responsiveness optimization or I16 acceptance claim.",
        "Small profile pilots have weak tail estimates; sample counts are explicit.",
        "Native full flow is POST plus subsequent GET, not browser paint. Cold-start",
        "responses are not prediction throughput. Browser double RAF is a paint",
        "opportunity, not hardware presentation; the current app has no pending state.", ""]
    lines.extend(native_table(args.native) + [""] + browser_table(args.browser) + [""])
    lines.extend(stage_table(args.server_log, args.native, args.browser) + [""] + runtime_table(args.runtime))
    args.output.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
