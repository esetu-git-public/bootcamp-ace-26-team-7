# backend/actions.py
#
# Action plans grounded in standard pavement-maintenance practice
# (DOT/FHWA-style guidance): crack sealing, patching, and pothole
# repair procedures scaled by severity.

ACTION_PLANS = {
    "Cracks": {
        "Low": {
            "action": "Monitor",
            "priority": "Routine",
            "steps": [
                "Log crack location, length, and width for tracking",
                "No sealing needed yet — narrow/tight cracks with no spalling",
                "Re-inspect within 6-12 months",
            ],
        },
        "Medium": {
            "action": "Crack Sealing (Rout and Seal)",
            "priority": "Scheduled",
            "steps": [
                "Clean crack of debris, vegetation, and loose material",
                "Rout crack (~1/8 in removed each side, ~3/8 in deep) if width warrants it",
                "Apply hot-pour rubberized sealant; avoid application right after rain",
                "Schedule within 1-3 months, ideally spring or fall",
            ],
        },
        "High": {
            "action": "Full-Depth Crack Repair",
            "priority": "Urgent",
            "steps": [
                "Assess for alligator/fatigue cracking indicating base failure",
                "If structural: full-depth patch removing affected area down to base",
                "If isolated: rout and seal plus close monitoring",
                "Repair within 2-4 weeks to prevent pothole formation",
            ],
        },
    },
    "Patch": {
        "Low": {
            "action": "Monitor",
            "priority": "Routine",
            "steps": [
                "Visually inspect patch edges for separation or ride quality loss",
                "Re-inspect within 6 months",
            ],
        },
        "Medium": {
            "action": "Patch Edge Reseal",
            "priority": "Scheduled",
            "steps": [
                "Seal patch perimeter to stop water infiltration at the seam",
                "Fill any settling or minor surface irregularities",
                "Schedule within 1-2 months",
            ],
        },
        "High": {
            "action": "Patch Removal and Replacement",
            "priority": "Urgent",
            "steps": [
                "Cut out the failed patch to sound surrounding pavement",
                "Inspect and repair subgrade/base if compromised",
                "Repave full-depth with compacted hot-mix asphalt",
                "Repair within 2-3 weeks",
            ],
        },
    },
    "Potholes": {
        "Low": {
            "action": "Temporary Patch (Throw-and-Roll)",
            "priority": "Scheduled",
            "steps": [
                "Fill with cold-mix asphalt as an interim measure",
                "Compact by vehicle traffic or hand tamper",
                "Schedule permanent repair within 1 month",
            ],
        },
        "Medium": {
            "action": "Permanent Patch Repair",
            "priority": "Urgent",
            "steps": [
                "Square off and clean pothole edges",
                "Apply hot-mix asphalt patch in compacted lifts",
                "Seal the patch perimeter to prevent water intrusion and recurrence",
                "Repair within 1-2 weeks",
            ],
        },
        "High": {
            "action": "Emergency Full-Depth Repair",
            "priority": "Immediate",
            "steps": [
                "Place warning signage/barricades immediately — safety hazard",
                "Dispatch repair crew within 24-48 hours",
                "Full-depth removal and base reconstruction, not just surface fill",
                "Compact thoroughly in lifts to prevent early failure",
            ],
        },
    },
    "Surface Defects": {
        "Low": {
            "action": "Monitor",
            "priority": "Routine",
            "steps": [
                "Document extent of raveling, weathering, or minor wear",
                "Re-inspect within 6-12 months",
            ],
        },
        "Medium": {
            "action": "Surface Treatment (Seal/Slurry Coat)",
            "priority": "Scheduled",
            "steps": [
                "Apply fog seal, seal coat, or slurry seal depending on extent",
                "Best done as preventive treatment before deterioration worsens",
                "Schedule within 2-3 months",
            ],
        },
        "High": {
            "action": "Milling and Resurfacing (Overlay)",
            "priority": "Urgent",
            "steps": [
                "Mill affected surface layer to remove damaged material",
                "Apply new hot-mix asphalt overlay",
                "Address any underlying drainage issues first",
                "Schedule within 1 month to prevent structural damage",
            ],
        },
    },
}


def get_action_plan(predicted_class, severity_label):
    """Returns the action plan dict for a defect_type + severity, or None."""
    if predicted_class not in ACTION_PLANS:
        return None
    if severity_label not in ACTION_PLANS[predicted_class]:
        return None
    return ACTION_PLANS[predicted_class][severity_label]