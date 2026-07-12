# backend/cost.py

CURRENCY = "USD"

# Cost ranges: {defect_type: {severity: (low, high)}}
COST_RANGES = {
    "Cracks": {
        "Low": (500, 1500),
        "Medium": (1500, 3500),
        "High": (3500, 6000),
        "Critical": (6000, 12000),
    },
    "Patch": {
        "Low": (1000, 2500),
        "Medium": (2500, 5000),
        "High": (5000, 8000),
        "Critical": (8000, 15000),
    },
    "Potholes": {
        "Low": (100, 500),
        "Medium": (500, 2000),
        "High": (2000, 5000),
        "Critical": (5000, 10000),
    },
    "Surface Defects": {
        "Low": (500, 2000),
        "Medium": (2000, 5000),
        "High": (5000, 10000),
        "Critical": (10000, 20000),
    },
}

# Time ranges (in hours): {defect_type: {severity: (low_hrs, high_hrs)}}
TIME_RANGES = {
    "Cracks": {
        "Low": (1, 3),
        "Medium": (3, 8),
        "High": (8, 24),
        "Critical": (24, 72),
    },
    "Patch": {
        "Low": (2, 5),
        "Medium": (5, 12),
        "High": (12, 30),
        "Critical": (30, 80),
    },
    "Potholes": {
        "Low": (1, 2),
        "Medium": (2, 6),
        "High": (6, 16),
        "Critical": (16, 48),
    },
    "Surface Defects": {
        "Low": (2, 6),
        "Medium": (6, 16),
        "High": (16, 40),
        "Critical": (40, 120),
    },
}

def narrow_range(low, high, confidence):
    """
    Shrinks the range from both ends as confidence increases.
    confidence = 1.0 -> tightest range (25% shrink from each end)
    confidence = 0.0 -> full original range
    """
    shrink = (1 - confidence) * 0.5 if confidence <= 1 else 0
    # invert so higher confidence = more shrink, capped at 25% each side
    shrink_factor = (confidence) * 0.25  # 0 to 0.25
    range_span = high - low
    narrowed_low = low + range_span * shrink_factor
    narrowed_high = high - range_span * shrink_factor
    return round(narrowed_low), round(narrowed_high)


def estimate_repair_cost(predicted_class, severity_label, confidence):
    if predicted_class not in COST_RANGES:
        raise ValueError(f"Unknown defect type: {predicted_class}")
    if severity_label not in COST_RANGES[predicted_class]:
        raise ValueError(f"Unknown severity level: {severity_label}")

    low, high = COST_RANGES[predicted_class][severity_label]
    narrowed_low, narrowed_high = narrow_range(low, high, confidence)

    return {
        "low": narrowed_low,
        "high": narrowed_high,
        "display": f"${narrowed_low:,} - ${narrowed_high:,}",
        "currency": CURRENCY,
    }


def estimate_repair_time(predicted_class, severity_label, confidence):
    if predicted_class not in TIME_RANGES:
        raise ValueError(f"Unknown defect type: {predicted_class}")
    if severity_label not in TIME_RANGES[predicted_class]:
        raise ValueError(f"Unknown severity level: {severity_label}")

    low, high = TIME_RANGES[predicted_class][severity_label]
    narrowed_low, narrowed_high = narrow_range(low, high, confidence)

    # convert to a readable display (hours vs days)
    if narrowed_high >= 24:
        display = f"{narrowed_low/24:.1f} - {narrowed_high/24:.1f} days"
        unit = "days"
    else:
        display = f"{narrowed_low} - {narrowed_high} hours"
        unit = "hours"

    return {
        "low": narrowed_low,
        "high": narrowed_high,
        "display": display,
        "unit": unit,
    }
