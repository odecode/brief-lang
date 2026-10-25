#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Correctness-checked current POST -> GET baseline; never an application server."""
import argparse
import concurrent.futures
import json
import math
import os
import pathlib
import statistics
import subprocess
import time
import urllib.request


def request(base, path, payload=None, operation=""):
    data = None if payload is None else json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"} if data else {}
    if operation:
        headers["X-Recommender-Trace"] = operation
    started = time.monotonic_ns()
    query = urllib.request.Request(base + path, data=data, headers=headers)
    with urllib.request.urlopen(query, timeout=120) as response:
        assert response.status == 200
        result = json.load(response)
    if "error" in result:
        raise AssertionError(result)
    return result, (time.monotonic_ns() - started) / 1e6


def sql(statement):
    return subprocess.check_output(["psql", "-w", "-h", "127.0.0.1", "-U", "briev_test",
        "-d", "briev_recommender_i01", "-v", "ON_ERROR_STOP=1", "-Atc", statement], text=True).strip()


def account(base, label, count):
    username = "i01_" + label + "_" + str(time.time_ns())
    request(base, "/register", {"username": username, "password": "baseline-only"})
    owner = int(sql(f"SELECT id FROM accounts WHERE username='{username}'"))
    if count:
        sql(f"INSERT INTO ratings SELECT {owner}, item, 1+item%5, 1 "
            f"FROM generate_series(0,{count-1}) AS item")
    login, _ = request(base, "/login", {"username": username, "password": "baseline-only"})
    return {"username": username, "owner": owner, "token": login["token"], "count": count}


def wait_ready(base):
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        try:
            movies, _ = request(base, "/movies")
            assert len(movies["movies"]) == 1682
            return
        except OSError:
            time.sleep(.1)
    raise TimeoutError("baseline server did not become ready")


def operation(base, profile, sequence, item=None):
    item = (0 if profile["count"] else 100) if item is None else item
    rating = 1 + sequence % 5
    identity = f"native_{profile['owner']}_{sequence}"
    _, post_ms = request(base, "/rating", {"token": profile["token"],
        "item_id": item, "rating": rating}, identity)
    state, get_ms = request(base, "/state?token=" + profile["token"], operation=identity)
    assert state["account"]["id"] == profile["owner"]
    assert sum(row["item_id"] == item and row["rating"] == rating for row in state["ratings"]) == 1
    count = len(state["ratings"])
    if count < 5:
        assert state["cold_start"] is True and not state.get("recommendations")
    else:
        recommendations = state["recommendations"]
        assert len(recommendations) == 5
        rated = {row["item_id"] for row in state["ratings"]}
        assert all(row["item_id"] not in rated and math.isfinite(row["score"])
                   and 1 <= row["score"] <= 5 for row in recommendations)
        assert recommendations == sorted(recommendations, key=lambda row: (-row["score"], row["item_id"]))
    return {"operation": identity, "initial_ratings": profile["count"], "actual_ratings": count,
            "post_ms": post_ms, "get_ms": get_ms, "flow_ms": post_ms + get_ms}


def summarize(rows):
    result = {"samples": len(rows)}
    if not rows:
        return result
    for key in ("post_ms", "get_ms", "flow_ms"):
        values = sorted(row[key] for row in rows)
        result[key] = {"p50": statistics.median(values),
            "p95": values[math.ceil(.95 * len(values))-1],
            "p99": values[math.ceil(.99 * len(values))-1]}
    return result


def resources(pid):
    if not pid:
        return None
    status = pathlib.Path(f"/proc/{pid}/stat").read_text().split()
    memory = pathlib.Path(f"/proc/{pid}/status").read_text().splitlines()
    peak = next(int(line.split()[1]) * 1024 for line in memory if line.startswith("VmHWM:"))
    return {"cpu_seconds": (int(status[13]) + int(status[14])) / os.sysconf("SC_CLK_TCK"),
            "rss_bytes": int(status[23]) * os.sysconf("SC_PAGE_SIZE"),
            "server_lifetime_peak_rss_bytes": peak,
            "descriptors": len(list(pathlib.Path(f"/proc/{pid}/fd").iterdir()))}


def single_profile(args, profile):
    for warmup in range(3):
        operation(args.base, profile, warmup)
    return [operation(args.base, profile, sequence + 3) for sequence in range(args.samples)]


def stream_profile(args, profile):
    completed = []
    for sequence in range(args.samples):
        try:
            completed.append(operation(args.base, profile, sequence))
        except Exception as error:
            completed.append({"error": str(error), "owner": profile["owner"], "sequence": sequence,
                              "outcome": "unknown; no retry issued"})
    return completed


def measure_profiles(args, profiles):
    rows, errors = [], []
    if args.concurrency == 1:
        for profile in profiles:
            rows.extend(single_profile(args, profile))
        fifth = None
        if profiles[1]["count"] == 4:
            fifth = operation(args.base, profiles[1], args.samples + 3, item=100)
        return rows, errors, fifth
    # Exactly one outstanding operation per owner; all owners progress concurrently.
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        for batch in pool.map(lambda profile: stream_profile(args, profile), profiles):
            rows.extend(row for row in batch if "error" not in row)
            errors.extend(row for row in batch if "error" in row)
    return rows, errors, None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://127.0.0.1:18082")
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--samples", type=int, default=200)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--server-pid", type=int)
    parser.add_argument("--profile-count", type=int, choices=(0, 4, 5, 20, 100))
    args = parser.parse_args()
    if args.samples < 1 or args.concurrency not in (1, 20, 100):
        parser.error("positive samples and concurrency 1, 20 or 100 required")
    wait_ready(args.base)
    profiles = [account(args.base, str(idx), args.profile_count if args.profile_count is not None
                        else (0, 4, 5, 20, 100)[idx % 5])
                for idx in range(max(5, args.concurrency))]
    if args.prepare_only:
        args.output.write_text(json.dumps({"profiles": [
            {key: value for key, value in profile.items() if key != "token"}
            for profile in profiles]}, indent=2))
        return
    started = time.monotonic()
    resources_before = resources(args.server_pid)
    rows, errors, fifth = measure_profiles(args, profiles)
    elapsed = time.monotonic() - started
    args.output.write_text(json.dumps({"base": args.base, "clock": "client monotonic_ns",
        "elapsed_seconds_including_warmups": elapsed,
        "successful_operations_per_second_including_warmups": len(rows) / elapsed,
        "resources_before": resources_before, "resources_after": resources(args.server_pid),
        "errors": errors,
        "concurrency": args.concurrency, "warmups_per_profile": 3 if args.concurrency == 1 else 0,
        "profiles": [{key: value for key, value in profile.items() if key != "token"} for profile in profiles],
        "first_fifth": fifth, "summary": summarize(rows), "rows": rows}, indent=2))
    print(json.dumps(summarize(rows), indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
