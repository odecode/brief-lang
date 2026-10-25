# fix(lexer): decode backslash-r escape in regular string and char literals

## Summary

A plain "\r\n" lexed to the FOUR literal characters (backslash, r, backslash, n) instead of the two bytes CR LF. CRLF-framed wire protocols (HTTP, websocket handshakes) could not express their line terminator in a String, which blocked building the net stack. This fix decodes backslash-r to U+000D in the regular-string and char-literal lanes, restoring parity with the byte-string lane.

## The bug

Discovered building lib/std/net/http.bv (recommender-app Task 3): the incremental HTTP request parser searches the accumulated bytes for the header terminator CRLF-CRLF and never found it.

### Controlled A/B (discriminator)

- `"ab\r\n\r\ncd" .^Length` printed 10 (expected 8).
- Byte 2 = 92 (backslash), byte 3 = 114 (r): the backslash and r survived as text.
- The byte-string lane (#b"...") decoded backslash-r correctly via decode_byte_escape.

So the gap was the regular-string / char lanes only: byte-string backslash-r works, regular-string backslash-r does not.

## Root cause

src/lexer.rs:
- unescape_string handled \\n \\t \\\\ \" \\0 \\x \\u but its `other = arm passed backslash-r through as a literal backslash + r.
- The Char-literal handler likewise lacked a backslash-r case.
- decode_byte_escape already had Some(r) =, so the three lanes had drifted apart.

## The fix

- Add the r arm (push U+000D) to unescape_string.
- Add the backslash-r case to the Char handler.

This restores parity with the byte-string lane and the C escape family. It is not a workaround: the carriage-return escape belongs in the language, and the interpreter path already treated it correctly (the interpreter is the reference).

## Tests

- test_string_carriage_return_escape: "\r\n" lexes to two bytes CR LF; "a\r\n\r\nb" round-trips the CRLF-CRLF header terminator.
- backslash-r case added to test_char_literals.

cargo test --lib green.

## Verification

- lib/std/net/http.bv incremental parser now finds the CRLF-CRLF header terminator.
- scratch harness ws_accept.bv (RFC 6455 known vector) and ws_roundtrip.bv (frame round-trip) build and run on top of this fix.

## Merge order

Independent fix, cut from main; no dependency on the other two fix branches. The feature branch feat/net-stack-http-websocket depends on this fix (it cannot express CRLF framing without it).

## Files changed

- src/lexer.rs: decode backslash-r in the string and char lanes; +2 regression tests.
- BUGS.md: entry documenting the bug and fix.
