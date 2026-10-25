#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Measure one eligible save while this test's refresh worker waits on a DB lock."""
import json
import os
import pathlib
import signal
import subprocess
import sys
import time
from native_baseline import account, operation, request, sql


def acquire_lock(blocker):
    blocker.stdin.write("BEGIN; LOCK TABLE baseline_ratings IN ACCESS EXCLUSIVE MODE; SELECT 'locked';\n")
    blocker.stdin.flush()
    while blocker.stdout.readline().strip() != "locked":
        if blocker.poll() is not None:
            raise RuntimeError(blocker.stderr.read())


def blocked_worker(children_file):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        children = children_file.read_text().split()
        if children and int(sql("SELECT count(*) FROM pg_stat_activity WHERE "
                               "datname=current_database() AND wait_event_type='Lock'")) > 0:
            assert len(children) == 1
            return int(children[0])
        time.sleep(.1)
    raise AssertionError("refresh worker did not reach the controlled lock")


def main():
    server = int(sys.argv[1])
    output = pathlib.Path(sys.argv[2])
    children_file = pathlib.Path(f"/proc/{server}/task/{server}/children")
    assert not children_file.read_text().strip(), "another refresh is active"
    profile = account("http://127.0.0.1:18082", "refresh", 5)
    command = ["psql", "-w", "-h", "127.0.0.1", "-U", "briev_test",
               "-d", "briev_recommender_i01", "-v", "ON_ERROR_STOP=1", "-At"]
    worker = None
    with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True, bufsize=1) as blocker:
        try:
            acquire_lock(blocker)
            request("http://127.0.0.1:18082", "/admin/refresh", {})
            worker = blocked_worker(children_file)
            result = operation("http://127.0.0.1:18082", profile, 0)
            assert int(sql("SELECT count(*) FROM pg_stat_activity WHERE "
                           "datname=current_database() AND wait_event_type='Lock'")) > 0
        finally:
            # Kill only the refresh child this probe created, while its read is
            # still blocked. Prevent installation/recomputation from changing the
            # shared baseline geometry for subsequent load measurements.
            if worker and str(worker) in children_file.read_text().split():
                os.kill(worker, signal.SIGTERM)
            blocker.stdin.write("ROLLBACK;\n\\q\n")
            blocker.stdin.flush()
            blocker.wait(timeout=5)
    deadline = time.monotonic() + 10
    while pathlib.Path(f"/proc/{worker}").exists() and time.monotonic() < deadline:
        time.sleep(.1)
    assert not pathlib.Path(f"/proc/{worker}").exists(), "test refresh child was not reaped"
    output.write_text(json.dumps({"worker": worker, "save_while_refresh_blocked": result,
                                 "test_child_reaped": True, "old_snapshot_retained": True}, indent=2))


if __name__ == "__main__":
    main()
