#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Controlled baseline: block writes in the isolated DB and observe reactor delay."""
import concurrent.futures
import json
import pathlib
import subprocess
import sys
import time
from native_baseline import account, operation, request


def main():
    base = "http://127.0.0.1:18082"
    profile = account(base, "blocked", 5)
    command = ["psql", "-w", "-h", "127.0.0.1", "-U", "briev_test",
               "-d", "briev_recommender_i01", "-v", "ON_ERROR_STOP=1", "-At"]
    with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True, bufsize=1) as blocker:
        blocker.stdin.write("BEGIN; LOCK TABLE ratings IN SHARE MODE; SELECT 'locked';\n")
        blocker.stdin.flush()
        while blocker.stdout.readline().strip() != "locked":
            if blocker.poll() is not None:
                raise RuntimeError(blocker.stderr.read())
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            save = pool.submit(operation, base, profile, 0)
            time.sleep(.25)
            catalogue = pool.submit(request, base, "/movies")
            time.sleep(1)
            before_release = {"save_completed": save.done(), "catalogue_completed": catalogue.done()}
            blocker.stdin.write("ROLLBACK;\n\\q\n")
            blocker.stdin.flush()
            saved = save.result(timeout=120)
            movies, catalogue_ms = catalogue.result(timeout=120)
        assert len(movies["movies"]) == 1682
        assert not before_release["save_completed"]
        blocker.wait(timeout=5)
    result = {"before_release": before_release, "save": saved,
              "catalogue_ms": catalogue_ms, "held_after_submit_ms": 1250,
              "interpretation": "Current synchronous baseline; not prediction-independence acceptance."}
    pathlib.Path(sys.argv[1]).write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
