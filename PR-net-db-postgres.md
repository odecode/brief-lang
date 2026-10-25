# feat(net): PostgreSQL v3 wire client lib/std/db/pg.bv (net stack L3a)

## Summary

A pure-Briev PostgreSQL v3 wire-protocol client - the L3a layer of the net stack. It lets a Briev backend connect to PostgreSQL, authenticate, run simple and parameterized queries, and decode rows, built entirely on the L1 byte buffers and L2 TCP socket (no libc, no third-party driver).

## Motivation

recommender-app Task 2. The app persists accounts and ratings in PostgreSQL; this is the client side of the protocol between the raw socket and the account/rating services.

## The wire shape

Every message after startup is `type:u8 | length:i32be | payload`, where length counts the 4 length bytes and the payload but NOT the type byte. The StartupMessage is the one exception: `length:i32be | protocol:i32be | (key NUL value NUL)* NUL`, no type byte.

## What it implements

- Framing (`pg_send_msg`/`pg_read_msg`): the full frame is assembled into a FIXED ByteBuf sized to the exact total, so there is no GrowBuf move hazard; reads parse the 5-byte header then the len-4 payload.
- StartupMessage (`pg_send_startup`): protocol 196608, user/database cstr pairs.
- Handshake (`pg_handshake`): trust auth (AuthenticationOk, code 0), records BackendKeyData, drains to ReadyForQuery. md5 is the documented next step; SCRAM is deferred.
- Simple Query (`pg_simple_query`) + a message pump decoding RowDescription / DataRow / CommandComplete.
- Row model (`PgResult`): row-major text fields + shape, with bounds-contracted `pg_row_int` / `pg_row_text`; SQL NULL (len -1) decodes to the empty string.
- Extended/parameterized query (`pg_exec`): Parse / Bind / Describe / Execute / Sync, values BOUND not interpolated.
- ErrorResponse parsed into SQLSTATE + message on the result.

## Why parameterized queries

A value interpolated into SQL text lets a crafted input escape the quotes and run arbitrary SQL (injection). The extended protocol sends the SQL with $1..$n placeholders once via Parse, then the values separately via Bind - the server never re-parses the values as SQL, so there is nothing to escape. All app CRUD uses this path (the operating contract secure-by-default stance).

## The length-backpatch / GrowBuf hazard

GrowBuf may move its allocation on growth, so a cached interior pointer would dangle. The frame length is therefore computed into a FIXED ByteBuf (known total) rather than backpatched into a moving GrowBuf - no cached address survives a grow.

## Tests / verification

- brievc check clean on lib/std/db/pg.bv.
- scratch/pg_encode.bv (not committed; under scratch/) verifies the encoding byte-for-byte without a live server:
  - the SELECT 1 Q frame: type=81, len=13, payload SELECT 1 + NUL;
  - the Bind payload for [alice, 42]: 0 0 | 0 0 | 0 2 | 0 0 0 5 alice | 0 0 0 2 42 | 0 0.
- The live-server integration (connect/auth/query against a trust-auth PostgreSQL, subtask 2.9) is the optional step and needs a running server; everything that does not require a server is verified.

## Dependency on other branches

This will NOT compile on main alone. It depends on:
- the net-stack L1 (bytes.bv) and L2 (socket.bv) branches it imports;
- fix/dot-call-stateful-state - the response path dot-calls stateful GrowBuf ByteSink writers (put_cstr/put_u32_be via grow_to_fit); without that fix the caller is emitted without %state.

Recommended merge order: the net-stack L1/L2 branches and the three compiler fixes first, then this.

## Files added

- lib/std/db/pg.bv
