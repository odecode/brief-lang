# JSON consume-or-error correctness

Task 12 exposed hangs on incomplete strings and acceptance of malformed JSON.
The prepared stdlib correction uses bounded recursive descent: every successful
step consumes input; every incomplete or invalid token returns an error. It
validates separators, complete framing, escapes, Unicode scalars/surrogates,
UTF-8, integer bounds and finite floating results. Contracts remain intact.

The standalone tests/fixtures/stdlib/json_parse_gate.bv exercises valid and invalid
literals, containers, strings, numeric endpoints and truncated input without any
application imports. Native result: all five groups true, exit 0 under timeout.
The complete server JSON gate also passes. No interpreter work is included.
Directory Praetor passes; full integration library suite is 3169 passed and the
38 environment failures explicitly accepted by the user, with no added names.

Keep the JSON regression separate from the application so this stdlib fix can
land independently. Related database import scoping and HTTP status descriptions
belong to their existing net-stack modules and are separate integration changes.
