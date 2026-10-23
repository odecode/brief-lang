#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Run the unmodified runtime suite in a private archive of a named commit."""
import argparse
import hashlib
import io
import json
import pathlib
import platform
import shutil
import subprocess
import tarfile
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=pathlib.Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    root = pathlib.Path(__file__).resolve().parents[2]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    compiler = args.compiler.resolve(strict=True)
    commit = subprocess.check_output(
        ["git", "rev-parse", args.commit], cwd=root, text=True).strip()
    metadata = {
        "commit": commit, "compiler": str(compiler),
        "compiler_sha256": hashlib.sha256(compiler.read_bytes()).hexdigest(),
        "machine": platform.uname()._asdict(),
        "clang": subprocess.check_output(["clang", "--version"], text=True),
        "command": "bash benchmarks/build_and_bench.sh --runtime",
        "shell_normalization": "CRLF to LF in private archive only",
    }
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2))
    archive = subprocess.check_output(["git", "archive", commit], cwd=root)
    with tempfile.TemporaryDirectory(prefix="briev-i01-runtime-") as temporary:
        checkout = pathlib.Path(temporary)
        with tarfile.open(fileobj=io.BytesIO(archive)) as files:
            files.extractall(checkout)
        for script in checkout.rglob("*.sh"):
            script.write_bytes(script.read_bytes().replace(b"\r\n", b"\n"))
        binary = checkout / "target/release/brievc"
        binary.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(compiler, binary)
        # The release compiler resolves native runtime archives relative to its
        # resource root. An archive of Git alone excludes these build outputs.
        metadata["runtime_archives"] = {}
        for name in ("libbriev_accel_rt.a", "libbriev_gpu_rt.a"):
            library = root / "target/compiler-in-briv" / name
            if not library.is_file():
                raise FileNotFoundError(f"Build the release runtime first: {library}")
            destination = checkout / "target/compiler-in-briv" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(library, destination)
            metadata["runtime_archives"][name] = hashlib.sha256(library.read_bytes()).hexdigest()
        with (output / "runtime.log").open("w") as log:
            result = subprocess.run(["bash", "benchmarks/build_and_bench.sh", "--runtime"],
                                    cwd=checkout, stdout=log, stderr=subprocess.STDOUT)
        metadata["exit_code"] = result.returncode
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2))
    print(json.dumps(metadata, indent=2))
    raise SystemExit(metadata["exit_code"])


if __name__ == "__main__":
    main()
