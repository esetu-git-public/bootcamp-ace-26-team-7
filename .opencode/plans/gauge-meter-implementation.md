# Gauge Meter Implementation Plan

## Overview
Add a semicircle gauge chart (speedometer-style) to visualize severity levels (Low, Medium, High, Critical) using Plotly's `go.Indicator`. The gauge will display on:
1. **Predict Page** - Full gauge in prediction results
2. **Dashboard Recent Card** - Compact gauge next to severity pill

---

## Changes Required

### 1. Add Two New Functions (after `severity_bars_html`, ~line 269)

```python
def severity_gauge_chart(severity_label: str, severity_score: float, height: int = 220):
    """Create a semicircle gauge chart for severity visualization."""
    if not PLOTLY_AVAILABLE:
        return None

    score_pct = severity_score * 100
    color = SEVERITY_COLOR.get(severity_label, "#999")
    gauge_colors = ["#2ecc71", "#f39c12", "#e74c3c", "#8b0000"]
    gauge_bounds = [0, 35, 65, 85, 100]

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score_pct,
        number={"suffix": "%", "font": {"size": 36, "color": color}},
        title={"text": f"Severity: {severity_label}", "font": {"size": 18, "color": "#1A1A2E"}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#B0B0C8", "tickfont": {"size": 10}},
            "bar": {"color": color, "thickness": 0.3},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 2,
            "bordercolor": "#E8EAF0",
            "steps": [
                {"range": [gauge_bounds[i], gauge_bounds[i+1]], "color": gauge_colors[i]}
                for i in range(4)
            ],
            "threshold": {
                "line": {"color": "white", "width": 3},
                "thickness": 0.75,
                "value": score_pct
            }
        }
    ))

    fig.update_layout(
        margin=dict(l=20, r=20, t=50, b=20),
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, -apple-system, sans-serif"},
    )
    return fig


def severity_gauge_chart_compact(severity_label: str, severity_score: float, height: int = 140):
    """Create a compact semicircle gauge for dashboard cards."""
    if not PLOTLY_AVAILABLE:
        return None

    score_pct = severity_score * 100
    color = SEVERITY_COLOR.get(severity_label, "#999")
    gauge_colors = ["#2ecc71", "#f39c12", "#e74c3c", "#8b0000"]
    gauge_bounds = [0, 35, 65, 85, 100]

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score_pct,
        number={"suffix": "%", "font": {"size": 24, "color": color}},
        title={"text": severity_label, "font": {"size": 13, "color": "#7A7A9E"}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#B0B0C8", "tickfont": {"size": 9}},
            "bar": {"color": color, "thickness": 0.25},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 1,
            "bordercolor": "#E8EAF0",
            "steps": [
                {"range": [gauge_bounds[i], gauge_bounds[i+1]], "color": gauge_colors[i]}
                for i in range(4)
            ],
            "threshold": {"line": {"color": "white", "width": 2}, "thickness": 0.6, "value": score_pct}
        }
    ))

    fig.update_layout(
        margin=dict(l=10, r=10, t=35, b=10),
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, -apple-system, sans-serif"},
    )
    return fig
```

### 2. Update Predict Page UI (~line 416)

Add a `gr.Plot` component for the gauge in the prediction results column:
```python
with gr.Column(scale=1):
    pred_results = gr.HTML('...')
    pred_gauge = gr.Plot(None, show_label=False, container=False)  # NEW
pred_report = gr.HTML("")
```

### 3. Update `run_predict_prediction` Function (~line 787)

Generate and return the gauge chart:
```python
# After creating results_html, before return:
gauge_fig = severity_gauge_chart(severity_label, severity_score)
return gr.update(value=results_html), gr.update(value=report_html), gr.update(value=gauge_fig)

# Update click handler outputs:
pred_run.click(
    fn=run_predict_prediction,
    inputs=[pred_upload, pred_class_selector, prediction_history],
    outputs=[pred_results, pred_report, pred_gauge],  # ADD pred_gauge
)
```

### 4. Update Dashboard Recent Card (`_recent_card`, ~line 646)

Add compact gauge next to severity pill in recent prediction card:
```python
def _recent_card(history):
    if not history:
        return ...
    latest = history[0]
    sev = latest.get("severity_label", "---")
    score = latest.get("severity_score", 0)
    thumb = latest.get("thumbnail")
    # ... existing code ...
    
    # Generate compact gauge
    gauge_fig = severity_gauge_chart_compact(sev, score)
    gauge_html = ""
    if gauge_fig:
        # Convert plotly fig to HTML for embedding in card
        import plotly.io as pio
        gauge_html = pio.to_html(gauge_fig, include_plotlyjs=False, full_html=False,
                                 config={"displayModeBar": False})
    
    return f"""<div class="card">...{gauge_html}..."""
```

### 5. Add `dash_gauge` to Dashboard UI (~line 397)

```python
with gr.Column(scale=1):
    dash_recent = gr.HTML('...')
    dash_gauge = gr.Plot(None, show_label=False, container=False)  # NEW
```

### 6. Update `_refresh_dashboard` Function (~line 683)

```python
def _refresh_dashboard(history):
    # ... existing code ...
    sev_counts, sev_total = severity_distribution(history)
    severity = severity_bars_html(sev_counts, sev_total)
    
    # Add gauge for latest prediction
    latest_gauge = None
    if history:
        latest = history[0]
        latest_gauge = severity_gauge_chart_compact(
            latest.get("severity_label", "---"),
            latest.get("severity_score", 0)
        )
    
    return stats, recent, chart, severity, latest_gauge

# Update click handler:
dash_run.click(
    fn=run_dash_prediction,
    inputs=[dash_upload, prediction_history],
    outputs=[prediction_history, dash_stats, dash_recent, dash_chart, dash_severity, dash_gauge],
)
```

---

## Color Zones (matching existing SEVERITY_COLOR)
- **Low** (0-35%): `#2ecc71` (Green)
- **Medium** (35-65%): `#f39c12` (Orange/Yellow)
- **High** (65-85%): `#e74c3c` (Red)
- **Critical** (85-100%): `#8b0000` (Dark Red)

---

## Testing
Run the app and verify:
1. Predict page shows full gauge with severity label and score
2. Dashboard recent card shows compact gauge
3. Colors match severity levels correctly
4. Gauge updates on new predictions

---

## Notes
- Uses existing `PLOTLY_AVAILABLE` flag for graceful fallback
- No new dependencies required (Plotly already imported)
- Follows existing code style and patterns
- Gauge thresholds match `SEVERITY_ORDER` boundaries from prediction logic