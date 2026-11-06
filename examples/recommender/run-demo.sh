#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
set -euo pipefail

rebuild_compiler=false
rebuild_app=false
usage() {
    cat <<'HELP'
Usage: run-demo.sh [--rebuild-app] [--rebuild-compiler | --rebuild]

Start local PostgreSQL if needed, then launch the existing demo builds.
  --rebuild-app       Rebuild the backend and frontend using the existing compiler.
  --rebuild-compiler  Rebuild the compiler and both app components.
  --rebuild           Rebuild the compiler and both app components.
  -h, --help         Show this help.
HELP
}
for arg in "$@"; do
    case "$arg" in
        --rebuild-app) rebuild_app=true ;;
        --rebuild-compiler|--rebuild) rebuild_compiler=true; rebuild_app=true ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $arg" >&2; usage >&2; exit 2 ;;
    esac
done

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

dataset_dir="${MOVIELENS_DIR:-/mnt/c/Users/wotto/AutAI/ml-100k}"
data_file="${UDATA_PATH:-$dataset_dir/u.data}"
item_file="${UITEM_PATH:-$dataset_dir/u.item}"
db_user="${PGUSER:-briev_test}"
db_name="${PGDATABASE:-briev_recommender_test}"
backend_port="${PORT:-8080}"
frontend_port="${FRONTEND_PORT:-8081}"
target_dir="${CARGO_TARGET_DIR:-$HOME/briev-target}"
build_profile="${BRIEV_BUILD_PROFILE:-release}"
if [[ "$build_profile" != release && "$build_profile" != debug ]]; then
    echo "BRIEV_BUILD_PROFILE must be 'release' or 'debug'" >&2
    exit 1
fi
compiler="$target_dir/$build_profile/brievc"
backend_out="$repo_root/target/recommender-demo"
frontend_out="$repo_root/target/recommender-web"

required_commands=(python3 pg_isready)
if "$rebuild_compiler"; then required_commands+=(cargo); fi
for command in "${required_commands[@]}"; do
    command -v "$command" >/dev/null || { echo "Required command not found: $command" >&2; exit 1; }
done
[[ -f "$data_file" ]] || { echo "MovieLens ratings file not found: $data_file" >&2; exit 1; }
[[ -f "$item_file" ]] || { echo "MovieLens title file not found: $item_file" >&2; exit 1; }

# The compiler invokes LLVM's verifier while building native targets as well
# as WebAssembly, so make the installed LLVM toolchain available to both.
if [[ -d /usr/lib/llvm-17/bin ]]; then
    PATH="/usr/lib/llvm-17/bin:$PATH"
    export PATH
fi

# Probe the same local endpoint used by the demo before attempting startup.
postgres_ready() {
    pg_isready -h "${PGHOST:-127.0.0.1}" -p "${PGPORT:-5432}" -U "$db_user" -d "$db_name" -t 1 >/dev/null 2>&1
}
if ! postgres_ready; then
    case "${PGHOST:-127.0.0.1}" in
        127.0.0.1|localhost|::1|/*) ;;
        *) echo "PostgreSQL at $PGHOST is unavailable; start that server and retry." >&2; exit 1 ;;
    esac
    echo "Starting PostgreSQL..."
    if [[ "$EUID" -eq 0 ]]; then
        service postgresql start
    else
        sudo service postgresql start
    fi
    for ((attempt = 0; attempt < 30; attempt++)); do
        if postgres_ready; then break; fi
        sleep 1
    done
    postgres_ready || { echo "PostgreSQL is not ready; check the postgresql service and PGHOST/PGPORT." >&2; exit 1; }
fi

if "$rebuild_compiler"; then
    echo "Building Briev compiler..."
    if [[ "$build_profile" == release ]]; then
        CARGO_TARGET_DIR="$target_dir" cargo build --release --bin brievc
    else
        CARGO_TARGET_DIR="$target_dir" cargo build --bin brievc
    fi
fi

if "$rebuild_app"; then
    [[ -x "$compiler" ]] || { echo "Compiler not found at $compiler; run with --rebuild." >&2; exit 1; }
    mkdir -p "$backend_out" "$frontend_out"
    echo "Building recommender backend..."
    "$compiler" build examples/recommender/server.bv --out "$backend_out"
    echo "Building browser frontend..."
    "$compiler" build examples/recommender/app.rbv --split --out "$frontend_out"
fi

backend="$backend_out/server"
[[ -x "$backend" ]] || { echo "Backend not found at $backend; run with --rebuild-app (or --rebuild)." >&2; exit 1; }
[[ -f "$frontend_out/app.html" ]] || { echo "Frontend not found at $frontend_out/app.html; run with --rebuild-app (or --rebuild)." >&2; exit 1; }

export PGUSER="$db_user" PGDATABASE="$db_name"
export UDATA_PATH="$data_file" UITEM_PATH="$item_file" PORT="$backend_port"
python3 -m http.server "$frontend_port" --bind 127.0.0.1 --directory "$frontend_out" &
http_pid=$!
cleanup() {
    kill "$http_pid" 2>/dev/null || true
    wait "$http_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Frontend: http://localhost:$frontend_port/app.html"
echo "Backend:  http://127.0.0.1:$backend_port"
echo "Database: $db_user@$db_name (PostgreSQL on ${PGHOST:-127.0.0.1}:${PGPORT:-5432})"
echo "Keep this terminal open; press Ctrl+C to stop the demo."
"$backend"
