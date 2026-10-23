# Publish PostgreSQL receive buffer lengths

Received PostgreSQL ErrorResponse frames returned empty SQLSTATE/message.
pg_read_msg (lib/std/db/pg.bv:72) filled raw allocations while ByteBuf.len stayed
zero; bounded C-string decoding correctly saw an empty prefix. buf_received
publishes the actual initialized prefix, preserving address/capacity and the
single allocation owner. Header and payload reads publish lengths after success;
truncated reads retain their failure path.

Standalone tests/fixtures/stdlib/pg_receive_gate.bv verifies the prefix view and
live SQLSTATE 22012 / division by zero preservation after rollback and connection
reuse. Verified with the integration compiler. Integration cargo build passes;
full library suite: 3164 passed, 38 known failures, none added. Praetor passes.

BASE: odecode/brief-lang:feat/net-db-postgres. Upstream main does not yet contain
the PostgreSQL client. Merge this focused correction into that pending feature
before landing the client upstream. This diff includes only the two stdlib files,
a standalone regression, byte-buffer ownership documentation, and bug logs.
It contains no application files or compiler source.

Native check (dedicated local trust-auth DB): build the standalone gate with
brievc, then run with PGUSER and PGDATABASE. It does not change database data.