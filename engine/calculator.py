from decimal import Decimal, ROUND_HALF_UP
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
