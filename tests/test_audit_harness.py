import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from engine.calculator import ProrationCalculator

def run_phase_1_tests():
    fixtures_path = os.path.join(os.path.dirname(__file__), "..", "fixtures", "golden_cases.json")
    with open(fixtures_path, "r") as f:
        test_cases = json.load(f)

    print("Running Phase 1 Verification Harness...\n")
    all_passed = True
    for case in test_cases:
        p = case["inputs"]
        calc = ProrationCalculator(acv=p["acv"], days_elapsed=p["days_elapsed"], discount=p["discount"])
        result = calc.audit(case["candidate_submission"])
        verdict_ok = result["verdict"] == case["expected_verdict"]
        error_ok = result["error_code"] == case["expected_error"]
        status = "[OK]" if (verdict_ok and error_ok) else "[FAIL]"
        if not (verdict_ok and error_ok):
            all_passed = False
        print(f"{status} {case['case_id']}: Expected {case['expected_verdict']} ({case['expected_error']}) -> Got {result['verdict']} ({result['error_code']})")

    if all_passed:
        print("\nPHASE 1 COMPLETE: All deterministic assertions verified successfully.")
    else:
        print("\nPHASE 1 FAILED: Logic mismatch detected.")
        sys.exit(1)

if __name__ == "__main__":
    run_phase_1_tests()
