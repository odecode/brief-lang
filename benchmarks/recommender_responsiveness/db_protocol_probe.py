#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Run as WSL root: retain only duration numbers for this test server's DB PID."""
import json
import pathlib
import re
import sys
from native_baseline import account, operation, sql


def main():
    profile = account("http://127.0.0.1:18082", "protocol", 5)
    backend = int(sql("SELECT pid FROM pg_stat_activity WHERE datname=current_database() "
                      "AND pid<>pg_backend_pid() AND backend_type='client backend' "
                      "ORDER BY backend_start LIMIT 1"))
    path = pathlib.Path("/var/log/postgresql/postgresql-12-main.log")
    with path.open() as log:
        log.seek(0, 2)
        result = operation("http://127.0.0.1:18082", profile, 0)
        appended = log.read()
    pattern = re.compile(r"\[" + str(backend) + r"\].*duration: ([0-9.]+) ms")
    durations = [float(found[1]) for line in appended.splitlines() if (found := pattern.search(line))]
    assert len(durations) == 12, f"Expected 4 extended queries × 3 duration records, got {len(durations)}"
    pathlib.Path(sys.argv[1]).write_text(json.dumps({"backend_pid": backend,
        "operation": result, "extended_queries": 4, "client_protocol_messages": 20,
        "postgres_duration_records_ms": durations, "postgres_duration_sum_ms": sum(durations),
        "scope": "Parse/Bind/Execute durations; no SQL text, credentials or cross-clock subtraction."}, indent=2))


if __name__ == "__main__":
    main()
