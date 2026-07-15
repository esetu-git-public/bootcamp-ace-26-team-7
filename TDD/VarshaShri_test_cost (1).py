"""
╔═══════════════════════════════════════════════════════════════╗
║  TDD — Varsha Sri (Developer)                                ║
║  Module: backend/cost.py — Cost Estimation & Range Narrowing ║
║  Run:  pytest TDD/VarshaSri_test_cost.py -v                  ║
╚═══════════════════════════════════════════════════════════════╝

Tests for pure logic functions: narrow_range, estimate_repair_cost,
estimate_repair_time.  No mocking or database required.
"""

import pytest
from backend.cost import (
    narrow_range,
    estimate_repair_cost,
    estimate_repair_time,
    COST_RANGES,
    TIME_RANGES,
    CURRENCY,
)


# ═══════════════════════════════════════════════════════════════
#  narrow_range(low, high, confidence)
#  Shrinks a [low, high] range proportionally based on a 0–1
#  confidence score.  Used to tighten cost/time estimates.
# ═══════════════════════════════════════════════════════════════

class TestNarrowRange:

    def test_zero_confidence_returns_full_range(self):
        """confidence=0 → no narrowing, original range returned."""
        low, high = narrow_range(100, 200, 0.0)
        assert low == 100
        assert high == 200

    def test_full_confidence_max_shrink(self):
        """confidence=1 → 25% shrink from each end.
           low += span * 0.25,  high -= span * 0.25"""
        low, high = narrow_range(100, 200, 1.0)
        assert low == 125   # 100 + 100*0.25
        assert high == 175  # 200 - 100*0.25

    def test_half_confidence_partial_shrink(self):
        """confidence=0.5 → shrink_factor = 0.5 * 0.25 = 0.125.
           low = 100 + 100*0.125 = 112.5 → round() = 112
           high = 200 - 100*0.125 = 187.5 → round() = 188"""
        low, high = narrow_range(100, 200, 0.5)
        assert low == 112
        assert high == 188

    def test_low_end_small_range(self):
        """Small range (10-20) with high confidence still ensures low ≤ high."""
        low, high = narrow_range(10, 20, 0.8)
        assert low > 10
        assert high < 20
        assert low <= high

    def test_zero_range_stays_zero(self):
        """low == high at any confidence → same value returned."""
        low, high = narrow_range(50, 50, 1.0)
        assert low == 50
        assert high == 50

    def test_low_equals_high_confidence_does_not_change(self):
        """When low==high, span is zero so confidence has no effect."""
        low, high = narrow_range(100, 100, 0.9)
        assert low == 100
        assert high == 100

    def test_confidence_greater_than_one(self):
        """confidence > 1 is clamped/truncated, never produces low > high."""
        low, high = narrow_range(100, 200, 2.0)
        assert low <= high

    def test_zero_confidence_zero_range(self):
        """[0,0] with confidence=0 → [0,0]."""
        low, high = narrow_range(0, 0, 0.0)
        assert low == 0
        assert high == 0

    @pytest.mark.parametrize("confidence", [0.0, 0.25, 0.5, 0.75, 1.0])
    def test_shrink_is_symmetric(self, confidence):
        """Midpoint stays roughly the same after symmetric narrowing."""
        mid = 1000
        half_range = 500
        low = mid - half_range
        high = mid + half_range
        narrowed_low, narrowed_high = narrow_range(low, high, confidence)
        assert narrowed_low <= narrowed_high
        actual_mid = (narrowed_low + narrowed_high) / 2
        assert abs(actual_mid - mid) <= 1  # rounding tolerance


# ═══════════════════════════════════════════════════════════════
#  estimate_repair_cost(predicted_class, severity, confidence)
#  Returns {"low", "high", "display", "currency"} for the given
#  defect type and severity, narrowed by confidence.
# ═══════════════════════════════════════════════════════════════

class TestEstimateRepairCost:

    def test_returns_all_keys(self):
        """Result dict contains exactly 4 keys."""
        result = estimate_repair_cost("Cracks", "Low", 0.5)
        assert set(result.keys()) == {"low", "high", "display", "currency"}

    def test_currency_is_usd(self):
        """Currency field always returns 'USD'."""
        result = estimate_repair_cost("Cracks", "Medium", 0.7)
        assert result["currency"] == CURRENCY
        assert result["currency"] == "USD"

    def test_display_format(self):
        """Display string uses '$low - $high' format."""
        result = estimate_repair_cost("Cracks", "Low", 0.0)
        assert result["display"] == "$500 - $1,500"

    def test_low_less_than_high(self):
        """For every class & severity combo, low <= high."""
        for cls in COST_RANGES:
            for sev in COST_RANGES[cls]:
                result = estimate_repair_cost(cls, sev, 0.5)
                assert result["low"] <= result["high"], f"{cls}/{sev}"

    def test_higher_severity_higher_cost(self):
        """Higher severity → strictly higher cost range."""
        low_cost = estimate_repair_cost("Potholes", "Low", 0.5)
        high_cost = estimate_repair_cost("Potholes", "High", 0.5)
        assert high_cost["low"] > low_cost["high"]

    def test_higher_confidence_narrower_range(self):
        """More confidence → narrower (high - low) span."""
        wide = estimate_repair_cost("Surface Defects", "Medium", 0.0)
        narrow = estimate_repair_cost("Surface Defects", "Medium", 1.0)
        wide_span = wide["high"] - wide["low"]
        narrow_span = narrow["high"] - narrow["low"]
        assert narrow_span < wide_span

    @pytest.mark.parametrize("cls", ["Cracks", "Patch", "Potholes", "Surface Defects"])
    def test_all_classes_return_valid(self, cls):
        """Every known class produces non-negative, valid range."""
        result = estimate_repair_cost(cls, "Medium", 0.5)
        assert result["low"] >= 0
        assert result["high"] > result["low"]

    def test_unknown_class_raises(self):
        """Unknown defect type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown defect type"):
            estimate_repair_cost("NonExistent", "Low", 0.5)

    def test_unknown_severity_raises(self):
        """Unknown severity level raises ValueError."""
        with pytest.raises(ValueError, match="Unknown severity"):
            estimate_repair_cost("Cracks", "NonExistent", 0.5)


# ═══════════════════════════════════════════════════════════════
#  estimate_repair_time(predicted_class, severity, confidence)
#  Returns {"low", "high", "display", "unit"} with the estimated
#  time range.  Unit switches from hours to days at ≥24hr.
# ═══════════════════════════════════════════════════════════════

class TestEstimateRepairTime:

    def test_returns_all_keys(self):
        """Result dict contains exactly 4 keys."""
        result = estimate_repair_time("Cracks", "Low", 0.5)
        assert set(result.keys()) == {"low", "high", "display", "unit"}

    def test_low_less_than_high(self):
        """For every class & severity, low <= high."""
        for cls in TIME_RANGES:
            for sev in TIME_RANGES[cls]:
                result = estimate_repair_time(cls, sev, 0.5)
                assert result["low"] <= result["high"], f"{cls}/{sev}"

    def test_units_hours_below_24(self):
        """Low severity → hours, with 'hours' in display."""
        result = estimate_repair_time("Cracks", "Low", 0.0)
        assert result["unit"] == "hours"
        assert "hours" in result["display"]

    def test_units_days_at_24_or_above(self):
        """Critical severity (≥24hr) → days."""
        result = estimate_repair_time("Cracks", "Critical", 0.0)
        assert result["unit"] == "days"
        assert "days" in result["display"]

    def test_critical_repair_time_display(self):
        """Critical repairs show days not weeks."""
        result = estimate_repair_time("Surface Defects", "Critical", 0.0)
        assert result["unit"] == "days"
        assert "/7" not in result["display"]

    @pytest.mark.parametrize("cls", ["Cracks", "Patch", "Potholes", "Surface Defects"])
    def test_all_classes_return_valid(self, cls):
        """Every known class produces valid time range."""
        result = estimate_repair_time(cls, "Medium", 0.5)
        assert result["low"] >= 0
        assert result["high"] >= result["low"]
        assert result["unit"] in ("hours", "days")

    def test_unknown_class_raises(self):
        """Unknown defect type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown defect type"):
            estimate_repair_time("NonExistent", "Low", 0.5)

    def test_unknown_severity_raises(self):
        """Unknown severity level raises ValueError."""
        with pytest.raises(ValueError, match="Unknown severity"):
            estimate_repair_time("Cracks", "NonExistent", 0.5)


# ═══════════════════════════════════════════════════════════════
#  Consistency Checks
#  COST_RANGES and TIME_RANGES dictionaries must stay in sync:
#  same class keys, same severity keys per class.
# ═══════════════════════════════════════════════════════════════

class TestCrossModuleConsistency:

    def test_same_class_keys(self):
        """Cost and time dicts share the same class names."""
        assert set(COST_RANGES.keys()) == set(TIME_RANGES.keys())

    def test_same_severity_keys_per_class(self):
        """Each class has the same severity levels in both dicts."""
        for cls in COST_RANGES:
            assert set(COST_RANGES[cls].keys()) == set(TIME_RANGES[cls].keys())

    def test_repair_time_display_integers(self):
        """Display values use whole numbers (no decimals)."""
        result = estimate_repair_time("Potholes", "Low", 0.0)
        parts = result["display"].split()
        assert all("." not in p for p in parts if p.isdigit())
