# fix(llvm): preserve register types and widths in concrete bit casts

## Summary

Casting a pointer-backed value to `Bits<N>` could return the original pointer register while describing it as an integer. A later encoding operation then emitted invalid LLVM IR. Integer inputs had a related problem: the same path emitted `trunc` for every width change, including widening.

This change emits conversions according to the actual source and destination representations. It also makes encoding-constructor calls respect the source register width and the constructor's argument ABI.

## Symptom and reproduction

This conversion should produce a String containing `hello`:

```briev
defn encode(source: String) -> String {
    let raw: Bits<64> = source as Bits<64>;
    term raw as String;
};
```

`String` is represented by a pointer to a `[length][bytes]` buffer. `Bits<64>` is represented by an LLVM `i64`. The cast must convert the pointer into an integer register before the raw-bit encoding route consumes it.

The failing reproduction instead emitted:

```llvm
%t19 = inttoptr i64 %t18 to ptr
%t23 = inttoptr i64 %t19 to ptr
%t21 = call ptr @briev_bits_to_str(ptr %t23)
```

The second instruction expects an integer, but `%t19` is a pointer. LLVM verification rejected it with:

```text
error: '%t19' defined with type 'ptr' but expected 'i64'
```

The integer case is illustrated by widening `Bits<8>` to `Bits<32>`. The previous code selected `trunc i8 ... to i32`, but truncation can only reduce width. Widening raw bits requires zero extension.

## Evidence isolating the cause

The native reproduction exercised `String → Bits<64> → String` and `String → Data → String` with the same input. The concrete Bits conversion failed LLVM verification before the pointer conversion was added. After correcting it, the executable printed `hello` through both routes.

The browser reproduction uses `Bits<32>` on wasm32 and checks three visible results: `hello` from raw-bit encoding, `hello` through Data, and `127` after widening `Bits<8>` to `Bits<32>`. These checks exercise emitted code as well as checking IR. No recommendation algorithm or network operation participates in the reproduction.

## Root cause

The concrete-width shortcut in [`emit_cast_path`, `src/backend/llvm/emit_expr.rs:8684`](https://github.com/odecode/brief-lang/blob/89ed2c8d/src/backend/llvm/emit_expr.rs#L8684) ran before the casting graph. The faulty code was:

```rust
if src_ll != tgt && src_ll.starts_with('i') {
    let reg = self.fun.gen_reg();
    writeln!(out, "{}{} = trunc {} {} to {}",
        indent, reg, src_ll, src.name, tgt).ok();
    return Some(TypedRegister { name: reg, ty: target.clone() });
}
return Some(TypedRegister { name: src.name.clone(), ty: target.clone() });
```

The first branch assumed every width difference was narrowing. The final return assumed any other source could be reused with a different type. Changing `TypedRegister.ty` changes Rust-side bookkeeping; it does not change the LLVM register's type or emit a conversion.

The encoding callback arm also assumed an `i64` source for pointer conversion and custom constructor arguments. Its boundary handling is in [`emit_expr.rs:9039`](https://github.com/odecode/brief-lang/blob/89ed2c8d/src/backend/llvm/emit_expr.rs#L9039).

## Fix and why it is sound

The concrete Bits path now follows the representations:

| Conversion | Emission |
|---|---|
| Pointer → `Bits<N>` | `ptrtoint ptr ... to iN` |
| Narrower integer → `Bits<N>` | `zext` |
| Wider integer → `Bits<N>` | `trunc` |
| Integer already of width N | Reuse the register |
| Other source representation | Continue through the casting graph |

Zero extension preserves the source bit pattern when widening. Truncation retains the existing narrowing behavior. Pointer conversion produces an actual integer register rather than relabelling a pointer.

The default encoding constructor converts the actual integer register width to a pointer. A registered constructor retains its canonical `i64` storage-word argument: narrower inputs are zero-extended, wider inputs are truncated, and 64-bit inputs are reused.

These decisions depend on representation and width, not on application-specific names or values. Upstream's existing casting graph and tuple ABI are preserved.

## Tests

- [`bit_encoding_override_receives_canonical_storage_word`](https://github.com/odecode/brief-lang/blob/89ed2c8d/src/backend/llvm/tests.rs#L12613) checks 8-, 32-, 64-, and 128-bit inputs against the custom constructor's `i64` argument ABI.
- [`bit_string_roundtrip_wasm.rbv`](https://github.com/odecode/brief-lang/blob/89ed2c8d/tests/fixtures/bit_string_roundtrip_wasm.rbv) covers pointer encoding, Data conversion, and widening. It is registered in the existing wasm fixture build test.
- [`browser_cast_tuple.mjs`](https://github.com/odecode/brief-lang/blob/89ed2c8d/tests/browser_cast_tuple.mjs) checks the generated wasm's visible results `hello`, `hello`, and `127`. It also runs the existing tuple-return fixture, expecting `6`, to check that tuple behavior is preserved.

## Verification and limits

On this clean branch, based on upstream `373e548e`:

```text
cargo test --lib bit_encoding_override_receives_canonical_storage_word
1 passed; 0 failed
```

On the integration tree, the native conversion executable and browser cast/tuple fixture passed. The standalone recommender rebuilt and passed its browser interaction fixture, including prediction-score display.

The final integration library run reported **3,422 passed and 11 failed**, with only the conformance sweep pending. The reported failures were the accepted SPIR-V environment cases. The user requested cancellation of the local sweep and delegated it to origin CI. The complete library suite is therefore not reported as locally green; the integration results are also distinct from the isolated branch check above.

## Merge order and files

Branch: `fix/concrete-bit-cast-widths`; commit: `89ed2c8d`; base: upstream `373e548e`.

This PR is independent of [the guarded tail-return fix, #56](https://github.com/Randozart/briev-lang/pull/56). Either can merge first. Both append to `BUGS.md`; retain both entries if those additions conflict.

The implementation change is confined to `src/backend/llvm/emit_expr.rs`. The other files contain the regression tests, fixture registration, bug record, and [`docs/architecture/concrete-bit-casts.md`](https://github.com/odecode/brief-lang/blob/89ed2c8d/docs/architecture/concrete-bit-casts.md). App changes and the obsolete tuple-test correction from the integration checkout are not included.
