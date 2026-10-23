import os
import json
from decimal import Decimal, ROUND_HALF_UP

# 1. Create directories
os.makedirs("specs", exist_ok=True)
os.makedirs("fixtures", exist_ok=True)
os.makedirs("engine", exist_ok=True)
os.makedirs("tests", exist_ok=True)

# 2. Write specs/saas_proration_v1.json
spec_content = {
  "workflow_id": "SAAS_PRORATION_CLAWBACK_V1",
  "domain": "Fintech & B2B SaaS Billing Operations",
  "parameters": {
    "cycle_days": 365,
    "penalty_rate": 0.20,
    "clawback_threshold_days": 180,
    "tax_rate": 0.15,
    "tolerance_cents": 0.05
  },
  "variable_ranges": {
    "annual_contract_value": {"min": 15000.00, "max": 100000.00, "step": 1000.00},
    "days_elapsed": {"min": 30, "max": 150},
    "discount_awarded": {"min": 1500.00, "max": 6000.00, "step": 500.00}
  },
  "error_taxonomy": {
    "ERR_ML_01": "DISCOUNT_CLAWBACK_OMITTED",
    "ERR_ML_02": "INVERTED_ORDER_OF_OPERATIONS",
    "ERR_ML_03": "GROSS_TAX_APPLICATION"
  }
}
with open("specs/saas_proration_v1.json", "w") as f:
    json.dump(spec_content, f, indent=2)

# 3. Write fixtures/golden_cases.json
fixtures_content = [
  {"case_id": "TC_001_PERFECT_EXECUTION", "inputs": {"acv": 36500.00, "days_elapsed": 73, "discount": 2500.00}, "candidate_submission": 23989.00, "expected_verdict": "PASS", "expected_error": None},
  {"case_id": "TC_002_FORGOT_CLAWBACK", "inputs": {"acv": 36500.00, "days_elapsed": 73, "discount": 2500.00}, "candidate_submission": 26864.00, "expected_verdict": "FAIL", "expected_error": "ERR_ML_01"},
  {"case_id": "TC_003_WRONG_ORDER_OF_OPERATIONS", "inputs": {"acv": 36500.00, "days_elapsed": 73, "discount": 2500.00}, "candidate_submission": 24564.00, "expected_verdict": "FAIL", "expected_error": "ERR_ML_02"},
  {"case_id": "TC_004_GROSS_TAX_APPLICATION", "inputs": {"acv": 36500.00, "days_elapsed": 73, "discount": 2500.00}, "candidate_submission": 25240.00, "expected_verdict": "FAIL", "expected_error": "ERR_ML_03"},
  {"case_id": "TC_005_RANDOM_ARITHMETIC_ERROR", "inputs": {"acv": 36500.00, "days_elapsed": 73, "discount": 2500.00}, "candidate_submission": 22100.50, "expected_verdict": "FAIL", "expected_error": "ERR_UNCLASSIFIED"}
]
with open("fixtures/golden_cases.json", "w") as f:
    json.dump(fixtures_content, f, indent=2)

# 4. Write engine/__init__.py
open("engine/__init__.py", "w").close()

# 5. Write engine/calculator.py
calculator_code = '''from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any

def round_cents(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

class ProrationCalculator:
    def __init__(self, acv: float, days_elapsed: int, discount: float, cycle_days: int = 365, penalty_rate: float = 0.20, tax_rate: float = 0.15, clawback_days: int = 180):
        self.acv = Decimal(str(acv))
        self.days_elapsed = Decimal(str(days_elapsed))
        self.discount = Decimal(str(discount))
        self.cycle_days = Decimal(str(cycle_days))
        self.penalty_rate = Decimal(str(penalty_rate))
        self.tax_rate = Decimal(str(tax_rate))
        self.clawback_days = Decimal(str(clawback_days))

    def get_ground_truth(self) -> Dict[str, Decimal]:
        days_rem = self.cycle_days - self.days_elapsed
        unearned = round_cents(self.acv * (days_rem / self.cycle_days))
        penalty = round_cents(unearned * self.penalty_rate)
        clawback = self.discount if self.days_elapsed < self.clawback_days else Decimal("0.00")
        pre_tax = max(Decimal("0.00"), unearned - penalty - clawback)
        tax = round_cents(pre_tax * self.tax_rate)
        final_payout = pre_tax + tax
        return {"unearned_gross": unearned, "etf_penalty": penalty, "clawback": clawback, "pre_tax_base": pre_tax, "tax_adjustment": tax, "final_payout": final_payout}

    def get_diagnostic_traps(self) -> Dict[str, Decimal]:
        truth = self.get_ground_truth()
        unearned = truth["unearned_gross"]
        penalty = truth["etf_penalty"]
        t1_base = max(Decimal("0.00"), unearned - penalty)
        err_ml_01 = t1_base + round_cents(t1_base * self.tax_rate)
        t2_base = max(Decimal("0.00"), unearned - self.discount)
        t2_pre_tax = max(Decimal("0.00"), t2_base - round_cents(t2_base * self.penalty_rate))
        err_ml_02 = t2_pre_tax + round_cents(t2_pre_tax * self.tax_rate)
        err_ml_03 = truth["pre_tax_base"] + round_cents(unearned * self.tax_rate)
        return {"ERR_ML_01": err_ml_01, "ERR_ML_02": err_ml_02, "ERR_ML_03": err_ml_03}

    def audit(self, candidate_payout: float, tolerance: float = 0.05) -> Dict[str, Any]:
        submission = round_cents(Decimal(str(candidate_payout)))
        truth = self.get_ground_truth()["final_payout"]
        tol = Decimal(str(tolerance))
        variance = submission - truth
        if abs(variance) <= tol:
            return {"verdict": "PASS", "error_code": None, "variance": 0.00}
        for err_code, trap_value in self.get_diagnostic_traps().items():
            if abs(submission - trap_value) <= tol:
                return {"verdict": "FAIL", "error_code": err_code, "variance": float(variance)}
        return {"verdict": "FAIL", "error_code": "ERR_UNCLASSIFIED", "variance": float(variance)}
'''
with open("engine/calculator.py", "w") as f:
    f.write(calculator_code)

# 6. Write tests/test_audit_harness.py
test_code = '''import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from engine.calculator import ProrationCalculator

def run_phase_1_tests():
    fixtures_path = os.path.join(os.path.dirname(__file__), "..", "fixtures", "golden_cases.json")
    with open(fixtures_path, "r") as f:
        test_cases = json.load(f)

    print("Running Phase 1 Verification Harness...\\n")
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
        print("\\nPHASE 1 COMPLETE: All deterministic assertions verified successfully.")
    else:
        print("\\nPHASE 1 FAILED: Logic mismatch detected.")
        sys.exit(1)

if __name__ == "__main__":
    run_phase_1_tests()
'''
with open("tests/test_audit_harness.py", "w") as f:
    f.write(test_code)

print("Files successfully generated.")