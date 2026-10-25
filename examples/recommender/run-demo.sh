#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
set -euo pipefail

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

for command in cargo python3; do
    command -v "$command" >/dev/null || { echo "Required command not found: $command" >&2; exit 1; }
done
[[ -f "$data_file" ]] || { echo "MovieLens ratings file not found: $data_file" >&2; exit 1; }
[[ -f "$item_file" ]] || { echo "MovieLens title file not found: $item_file" >&2; exit 1; }

echo "Building Briev compiler..."
if [[ "$build_profile" == release ]]; then
    CARGO_TARGET_DIR="$target_dir" cargo build --release --bin brievc
else
    CARGO_TARGET_DIR="$target_dir" cargo build --bin brievc
fi
[[ -x "$compiler" ]] || { echo "Compiler was not produced at $compiler" >&2; exit 1; }

mkdir -p "$backend_out" "$frontend_out"
echo "Building recommender backend..."
"$compiler" build examples/recommender/server.bv --out "$backend_out"
echo "Building browser frontend..."
if [[ -d /usr/lib/llvm-17/bin ]]; then
    PATH="/usr/lib/llvm-17/bin:$PATH" "$compiler" build examples/recommender/app.rbv --split --out "$frontend_out"
else
    "$compiler" build examples/recommender/app.rbv --split --out "$frontend_out"
fi

backend="$backend_out/server"
[[ -x "$backend" ]] || { echo "Backend executable was not produced at $backend" >&2; exit 1; }

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
echo "Database: $db_user@$db_name (local PostgreSQL on 127.0.0.1:5432)"
echo "Keep this terminal open; press Ctrl+C to stop the demo."
"$backend"
