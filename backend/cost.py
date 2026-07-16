# backend/cost.py

from backend.currency import convert_amount

CURRENCY = "USD"

# ---------------------------------------------------------
# Estimated Repair Cost (USD)
# Per SINGLE detected defect
# ---------------------------------------------------------

COST_RANGES = {
    "Cracks": {
        "Low": (15, 35),          # Hairline crack
        "Medium": (35, 70),       # Crack sealing
        "High": (70, 150),        # Multiple/long cracks
        "Critical": (150, 350),   # Structural cracking
    },

    "Patch": {
        "Low": (30, 60),          # Minor patch touch-up
        "Medium": (60, 120),      # Patch replacement
        "High": (120, 250),       # Failed patch replacement
        "Critical": (250, 500),   # Base repair
    },

    "Potholes": {
        "Low": (20, 40),          # Small pothole
        "Medium": (40, 80),       # Medium pothole
        "High": (80, 150),        # Large pothole
        "Critical": (150, 350),   # Deep pothole reconstruction
    },

    "Surface Defects": {
        "Low": (30, 70),          # Minor surface wear
        "Medium": (70, 150),      # Surface treatment
        "High": (150, 300),       # Small resurfacing
        "Critical": (300, 700),   # Major resurfacing
    },
}

# ---------------------------------------------------------
# Estimated Repair Time (Hours)
# ---------------------------------------------------------

TIME_RANGES = {
    "Cracks": {
        "Low": (1, 1),
        "Medium": (1, 2),
        "High": (2, 4),
        "Critical": (4, 8),
    },

    "Patch": {
        "Low": (1, 2),
        "Medium": (2, 3),
        "High": (3, 5),
        "Critical": (5, 8),
    },

    "Potholes": {
        "Low": (1, 1),
        "Medium": (1, 2),
        "High": (2, 4),
        "Critical": (4, 8),
    },

    "Surface Defects": {
        "Low": (2, 4),
        "Medium": (4, 8),
        "High": (8, 12),
        "Critical": (12, 24),
    },
}

CURRENCY_SYMBOLS = {
    "USD": "$",
    "INR": "₹",
    "EUR": "€",
    "GBP": "£",
}


def narrow_range(low, high, confidence):
    """
    confidence = 0.0 -> original range
    confidence = 1.0 -> range narrowed by 25%
    """
    confidence = max(0.0, min(confidence, 1.0))

    shrink_factor = confidence * 0.25
    span = high - low

    narrowed_low = low + span * shrink_factor
    narrowed_high = high - span * shrink_factor

    return round(narrowed_low), round(narrowed_high)


def estimate_repair_cost(
    predicted_class,
    severity_label,
    confidence,
    currency="USD",
):
    if predicted_class not in COST_RANGES:
        raise ValueError(f"Unknown defect type: {predicted_class}")

    if severity_label not in COST_RANGES[predicted_class]:
        raise ValueError(f"Unknown severity level: {severity_label}")

    low, high = COST_RANGES[predicted_class][severity_label]

    narrowed_low, narrowed_high = narrow_range(
        low,
        high,
        confidence,
    )

    currency = currency.upper()

    converted_low = convert_amount(
        narrowed_low,
        currency,
        base_currency="USD",
    )

    converted_high = convert_amount(
        narrowed_high,
        currency,
        base_currency="USD",
    )

    symbol = CURRENCY_SYMBOLS.get(
        currency,
        currency + " ",
    )

    return {
        "low": converted_low,
        "high": converted_high,
        "display": f"{symbol}{converted_low:,.0f} - {symbol}{converted_high:,.0f}",
        "currency": currency,
        "usd_low": narrowed_low,
        "usd_high": narrowed_high,
    }


def estimate_repair_time(
    predicted_class,
    severity_label,
    confidence,
):
    if predicted_class not in TIME_RANGES:
        raise ValueError(f"Unknown defect type: {predicted_class}")

    if severity_label not in TIME_RANGES[predicted_class]:
        raise ValueError(f"Unknown severity level: {severity_label}")

    low, high = TIME_RANGES[predicted_class][severity_label]

    narrowed_low, narrowed_high = narrow_range(
        low,
        high,
        confidence,
    )

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