//===----------------------------------------------------------------------===//
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
//===----------------------------------------------------------------------===//
use std::path::Path;
use std::process::Command;

#[test]
fn nonblocking_bounds_trap_before_syscall_or_memory_access() {
    if !cfg!(all(target_os = "linux", target_arch = "x86_64")) { return; }
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let output = tempfile::tempdir().expect("fixture directory");
    let build = Command::new(env!("CARGO_BIN_EXE_brievc"))
        .env("BRIEV_HOME", root)
        .arg("build").arg(root.join("tests/fixtures/load/nonblocking_limits_gate.bv"))
        .arg("--stdlib-path").arg(root.join("lib"))
        .arg("--config-dir").arg(root.join("config"))
        .arg("--out").arg(output.path())
        .output().expect("build bounds gate");
    assert!(build.status.success(), "{}", String::from_utf8_lossy(&build.stderr));
    for case in 0..=11 {
        let result = Command::new("timeout").arg("20")
            .arg(output.path().join("nonblocking_limits_gate"))
            .env("CASE", case.to_string()).output().expect("execute bounds gate");
        if case == 0 {
            assert!(result.status.success(), "{:?}", result.status);
            assert_eq!(result.stdout, b"nonblocking_valid_lifetime_ok\n");
            continue;
        }
        assert!(illegal_instruction(&result.status), "case {case}: {:?}", result.status);
        assert!(result.stdout.is_empty(), "invalid case {case} reached completion");
    }
}

fn illegal_instruction(status: &std::process::ExitStatus) -> bool {
    #[cfg(unix)]
    {
        use std::os::unix::process::ExitStatusExt;
        if status.signal() == Some(4) { return true; }
    }
    status.code() == Some(132)
}
