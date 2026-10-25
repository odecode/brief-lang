//===----------------------------------------------------------------------===//
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
//===----------------------------------------------------------------------===//
//! Native task-12 properties. Build server_property_gate.bv first, then set
//! RECOMMENDER_PROPERTY_BINARY to its executable. No database is needed here;
//! server_loop_gate.bv separately checks the complete database/socket path.
use proptest::prelude::*;
use std::process::Command;

fn native(mode: &str, variables: &[(&str, String)]) -> bool {
    let binary = std::env::var_os("RECOMMENDER_PROPERTY_BINARY")
        .expect("set RECOMMENDER_PROPERTY_BINARY to the built native server_property_gate");
    let output = Command::new(binary).env("PROPERTY_MODE", mode)
        .envs(variables.iter().map(|(key, value)| (*key, value)))
        .output().expect("run native property gate");
    assert!(output.status.success(), "{}", String::from_utf8_lossy(&output.stderr));
    let text = String::from_utf8(output.stdout).expect("UTF-8 property output");
    assert!(matches!(text.trim(), "true" | "false"), "unexpected output: {text}");
    text.trim() == "true"
}

proptest! {
    #![proptest_config(ProptestConfig::with_cases(128))]

    // Feature: recommender-app, Property 5: rating-value validation.
    // Validates Requirements 3.4; exercises JSON integer parsing and the same
    // validation boundary used before persistence by HTTP and live channels.
    #[test]
    #[ignore = "requires a built native property gate; run through run_server.sh"]
    fn rating_value_validation(value in prop_oneof![any::<i64>(), -2i64..9]) {
        prop_assert_eq!(native("rating", &[("PROPERTY_VALUE", value.to_string())]), (1..=5).contains(&value));
    }

    // Feature: recommender-app, Property 7: rating threshold gates recommendations.
    // Validates Requirements 3.1, 3.3.
    #[test]
    #[ignore = "requires a built native property gate; run through run_server.sh"]
    fn rating_threshold(count in 0i64..1683) {
        prop_assert_eq!(native("threshold", &[("PROPERTY_VALUE", count.to_string())]), count < 5);
    }

    // Feature: recommender-app, Property 20: live push delivered only to owning account.
    // Validates Requirements 5.5. The native gate calls the actual push predicate;
    // socket integration also verifies two owning channels and a foreign channel.
    #[test]
    #[ignore = "requires a built native property gate; run through run_server.sh"]
    fn live_owner_isolation(owner in 0i64..20, bound in 0i64..20, fd in -1i64..100,
                            upgraded in 0i64..2, closing in 0i64..2) {
        let variables = [("PROPERTY_OWNER",owner.to_string()), ("PROPERTY_BOUND_OWNER",bound.to_string()),
            ("PROPERTY_FD",fd.to_string()), ("PROPERTY_UPGRADED",upgraded.to_string()), ("PROPERTY_CLOSING",closing.to_string())];
        let expected = owner > 0 && owner == bound && fd >= 0 && upgraded == 1 && closing == 0;
        prop_assert_eq!(native("owner", &variables), expected);
    }
}
