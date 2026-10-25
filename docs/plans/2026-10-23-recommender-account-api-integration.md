# Recommender account API integration

**Status: IMPLEMENTED; runtime verification pending.** Restore compatibility between the current browser
client and native recommender server for account creation, sign-in, and the
immediate authenticated profile load.

## Evidence and hypothesis

The browser sends `/v1/register` and `/v1/login`; native dispatch recognizes
only `/register` and `/login`. The browser requires protocol version/type fields
plus an account ID and server epoch after sign-in, while the server returns only
`ok` and a token. Its next `/v1/state` request also expects a versioned state
envelope. The public `/movies` path already works, which isolates this to the
account/profile contract rather than basic networking.

Hypothesis: normalizing the `/v1` prefix at the HTTP routing boundary and
returning the versioned account/profile envelopes will make browser registration
and sign-in work while preserving existing unversioned API callers.

## Scope

1. Write a fresh process epoch once at server startup and retain it through
   server-state copies.
2. Normalize the `/v1` prefix after removing query text, so HTTP and WebSocket
   routing share the same versioned path behavior.
3. Return the protocol-v1 registration and authentication response fields
   consumed by `app.rbv`.
4. Return a protocol-v1 profile state envelope for both direct and cached state
   reads.
5. Extend the server API gate to exercise the versioned paths and response
   fields while retaining unversioned coverage.

## Gates and documentation

Run the server API and server loop gates against the dedicated recommender test
database, then build the server and browser bundle. Run the full library suite,
release build, affected-directory Praetor validation, and the documented browser
gate if the environment permits. No performance claims or benchmark run apply.

Update the recommender server and frontend wire-contract docs in the same
logical change. Add a BUGS entry only if the integration reveals an additional
compiler defect. Preserve existing rationale commentary in touched source.

## Baseline and results

| Check | Before change |
|---|---|
| `GET /movies` from browser | Pass, confirmed by user |
| Browser account creation/sign-in | Fails; frontend `/v1` paths and payload contract do not match server |
| Server API gate | Existing unversioned contract only; not run in this session yet |
| Build / tests / Praetor | Pending |

## Implementation and verification

The server now normalizes the optional `/v1/` route prefix, creates one random
process epoch and preserves it through `ServerState` snapshots, and returns the
versioned authentication and profile fields consumed by the browser. The API
gate now covers versioned registration, login and state requests while the
existing loop gate continues to cover legacy unversioned requests. Server and
frontend wire documentation and the bug ledger were updated.

`git diff --check` passes for the touched files. Runtime builds, API/loop gates,
the library suite and Praetor could not be run from this Windows session:
`cargo` is unavailable, the checked-in Linux `brievc` executable is denied by
Windows, and WSL returns `Wsl/E_ACCESSDENIED`. Run the task-12 server gate from
WSL against the dedicated test database before treating this patch as verified.
