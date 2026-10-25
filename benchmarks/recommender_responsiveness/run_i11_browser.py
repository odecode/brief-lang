#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Build same-revision recommender artifacts and run the real I11 browser gate."""
import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import time
import urllib.error
import urllib.request


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--api", default="http://127.0.0.1:18110")
    args = parser.parse_args()
    root = pathlib.Path(__file__).resolve().parents[2]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    compiler = args.compiler.resolve(strict=True)
    dataset = root / ".kiro/specs/recommender-app/u.data"
    if not os.environ.get("PGUSER") or not os.environ.get("PGDATABASE"):
        raise RuntimeError("Set PGUSER and PGDATABASE to a dedicated recommender test database.")
    if not dataset.is_file():
        raise RuntimeError(f"The recommender dataset is missing: {dataset}")

    native = output / "native"
    web = output / "web"
    native.mkdir()
    web.mkdir()
    env = {**os.environ, "PORT": "18110", "MAX_CONNECTIONS": "1024",
           "REFRESH_SECONDS": "86400", "LAMBDA_MILLI": "500",
           "UDATA_PATH": str(dataset), "CACHE_PATH": str(output / "model.snapshot")}
    commands = [
        [str(compiler), "build", "examples/recommender/server.bv", "--out", str(native)],
        [str(compiler), "build", "examples/recommender/app.rbv", "--split", "--out", str(web)],
    ]
    with (output / "build.log").open("w", encoding="utf-8") as log:
        for command in commands:
            subprocess.run(command, cwd=root, env=env, stdout=log,
                           stderr=subprocess.STDOUT, check=True)

    metadata = {
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "source_diff": subprocess.check_output(["git", "diff", "--", "examples/recommender"], cwd=root, text=True),
        "compiler_sha256": digest(compiler),
        "server_sha256": digest(native / "server"),
        "source_sha256": {path.name: digest(path) for path in sorted((root / "examples/recommender").iterdir())
                           if path.suffix in (".bv", ".rbv")},
        "dataset_sha256": digest(dataset),
        "web_artifacts_sha256": {path.name: digest(path) for path in sorted(web.iterdir()) if path.is_file()},
        "database": {key: env[key] for key in ("PGUSER", "PGDATABASE", "PGHOST", "PGPORT") if key in env},
        "api": args.api,
        "ports": {"server": 18110},
    }
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    api = args.api.rstrip("/")
    server_log = (output / "server.log").open("w", encoding="utf-8")
    server = subprocess.Popen([str(native / "server")], cwd=root, env=env,
                              stdout=server_log, stderr=subprocess.STDOUT)
    try:
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            if server.poll() is not None:
                raise RuntimeError(f"Recommender server exited with code {server.returncode}; see {output / 'server.log'}")
            try:
                with urllib.request.urlopen(api + "/movies", timeout=2) as response:
                    catalogue = json.load(response)
                if len(catalogue.get("movies", [])) == 1682:
                    break
            except (OSError, urllib.error.URLError, json.JSONDecodeError):
                time.sleep(0.2)
        else:
            raise TimeoutError(f"Recommender server did not become ready; see {output / 'server.log'}")

        node = os.environ.get("NODE", "node")
        subprocess.run([node, str(root / "tests/fixtures/recommender/browser_live_server.mjs"),
                        str(web), api], cwd=root, env=env, check=True)
        metadata["result"] = "pass"
        (output / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        print(f"I11 browser gate passed; build metadata and server log: {output}")
    finally:
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
        server_log.close()


if __name__ == "__main__":
    main()
