#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
# Run as root in the local WSL test environment. Never reset an existing DB.
set -euo pipefail
database=briev_recommender_i01
config=/etc/postgresql/12/main/pg_hba.conf
test "$(id -u)" = 0
runuser -u postgres -- createdb --owner=briev_test "$database"
temporary=$(mktemp)
trap 'rm -f "$temporary"' EXIT
printf 'host %s briev_test 127.0.0.1/32 trust # recommender-I01-only\n' "$database" > "$temporary"
cat "$config" >> "$temporary"
cat "$temporary" > "$config"
pg_ctlcluster 12 main reload
runuser -u postgres -- psql -v ON_ERROR_STOP=1 -d "$database" \
    -c 'ALTER DATABASE briev_recommender_i01 SET log_duration = on'
printf 'Created isolated %s; other database authentication is unchanged.\n' "$database"
