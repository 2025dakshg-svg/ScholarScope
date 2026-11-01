"""Test script to verify Google Apps Script webhook connectivity.

Appends an explicit dummy row (exactly 11 columns, empty score fields) to the Tests tab.
"""

from sheets import append_to_tests, check_webhook_health, EXPECTED_HEADERS


def main():
    print("Testing Google Apps Script Webhook...")
    print(f"Contract Schema: {len(EXPECTED_HEADERS)} columns -> {EXPECTED_HEADERS}")
    
    print("\nChecking webhook health via GET...")
    ok_health, health_msg = check_webhook_health()
    print(f"Webhook health: ok={ok_health}, message='{health_msg}'")

    print("\nSending explicit dummy connectivity row to 'Tests' tab...")
    ok, row_number, error_msg = append_to_tests(
        test_id="PING",
        topic="WEBHOOK CONNECTION TEST",
        version="V3",
        scoring=None,
        validation_status="CONNECTIVITY_CHECK",
        notes="connectivity check, not a test case"
    )

    if ok:
        print(f"SUCCESS: Saved dummy row to Tests tab! Real Row Number: {row_number}")
    else:
        print(f"FAILED: Could not save to Tests tab. Reason: {error_msg}")


if __name__ == "__main__":
    main()
