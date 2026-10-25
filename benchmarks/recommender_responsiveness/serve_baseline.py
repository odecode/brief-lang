#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Build and own isolated I01 services until interrupted (no existing PID killed)."""
import argparse
import hashlib
import json
import os
import pathlib
import signal
import subprocess
import time
import urllib.request


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def await_services(processes):
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        if any(process.poll() is not None for process in processes):
            raise RuntimeError("I01 service exited; inspect logs")
        try:
            query = urllib.request.Request("http://127.0.0.1:18082/movies")
            with urllib.request.urlopen(query, timeout=1) as response:
                assert len(json.load(response)["movies"]) == 1682
            return
        except OSError:
            time.sleep(.1)
    raise TimeoutError("I01 server did not become ready")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    root = pathlib.Path(__file__).resolve().parents[2]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    compiler = args.compiler.resolve(strict=True)
    dataset = root / ".kiro/specs/recommender-app/u.data"
    assert sum(1 for _ in dataset.open()) == 100000
    environment = {**os.environ, "PGUSER": "briev_test", "PGDATABASE": "briev_recommender_i01",
        "PORT": "18082", "MAX_CONNECTIONS": "1024", "REFRESH_SECONDS": "86400",
        "LAMBDA_MILLI": "500", "UDATA_PATH": str(dataset),
        "CACHE_PATH": str(output / "model.snapshot"), "RECOMMENDER_TRACE": "1"}
    environment["PATH"] = "/usr/lib/llvm-17/bin:" + environment["PATH"]
    with (output / "build.log").open("w") as log:
        for source, extra, destination in (("server.bv", [], output / "native"),
                                            ("app.rbv", ["--split"], output / "web")):
            subprocess.run([str(compiler), "build", "examples/recommender/" + source,
                            *extra, "--out", str(destination)], cwd=root,
                           env=environment, stdout=log, stderr=subprocess.STDOUT, check=True)
    metadata = {"source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "source_diff": subprocess.check_output(["git", "diff", "--", "examples/recommender"], text=True),
        "compiler_sha256": digest(compiler), "server_sha256": digest(output / "native/server"),
        "source_sha256": {path.name: digest(path) for path in (root / "examples/recommender").iterdir()
                          if path.suffix in (".bv", ".rbv")},
        "dataset_sha256": digest(dataset), "dataset": "943 users / 1682 items / 100000 ratings",
        "artifacts": {path.name: digest(path) for path in (output / "web").iterdir() if path.is_file()},
        "configuration": {key: environment[key] for key in ("PGUSER", "PGDATABASE", "PORT",
            "MAX_CONNECTIONS", "REFRESH_SECONDS", "LAMBDA_MILLI", "CACHE_PATH", "RECOMMENDER_TRACE")}}
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2))
    processes = []
    def stop(_signal, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        with (output / "server.log").open("w") as log, (output / "static.log").open("w") as static_log:
            processes.append(subprocess.Popen([str(output / "native/server")], cwd=root,
                                               env=environment, stdout=log, stderr=subprocess.STDOUT))
            processes.append(subprocess.Popen(["python3", "-m", "http.server", "18083", "--bind",
                "127.0.0.1", "--directory", str(output / "web")], stdout=static_log, stderr=subprocess.STDOUT))
            await_services(processes)
            metadata["pids"] = [process.pid for process in processes]
            (output / "metadata.json").write_text(json.dumps(metadata, indent=2))
            print("I01 ready: http://localhost:18083/app.html?api=http://127.0.0.1:18082", flush=True)
            while all(process.poll() is None for process in processes):
                time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    main()
