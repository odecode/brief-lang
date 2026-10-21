

## PostgreSQL receive buffer metadata (FIXED 2026-10-21)

pg_read_msg filled memory without publishing ByteBuf.len, so bounded error-field
scans returned empty SQLSTATE/message. buf_received now publishes initialized
header/body prefixes without copying or creating a second allocation owner.
Standalone tests/fixtures/stdlib/pg_receive_gate.bv passes prefix invariants and
live 22012/division by zero preservation through rollback and connection reuse.
Integration build passes; library suite: 3164 passed, 38 known failures, none new.
Praetor directory checks pass. No compiler source changes or performance claim.
Branch fix/pg-receive-length targets feat/net-db-postgres, absent from main.
