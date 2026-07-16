from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import inch
import os
from datetime import datetime


def generate_pdf(
    image_path,
    prediction,
    confidence,
    severity,
    repair_cost,
    repair_time,
):
    os.makedirs("reports", exist_ok=True)

    filename = f"inspection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join("reports", filename)

    doc = SimpleDocTemplate(filepath)

    styles = getSampleStyleSheet()

    title = styles["Heading1"]
    title.alignment = TA_CENTER

    story = []

    story.append(Paragraph("Surface Crack Inspection Report", title))
    story.append(Spacer(1, 20))

    if os.path.exists(image_path):
        img = Image(image_path, width=4 * inch, height=3 * inch)
        story.append(img)

    story.append(Spacer(1, 20))

    story.append(Paragraph(f"<b>Prediction:</b> {prediction}", styles["BodyText"]))
    story.append(Paragraph(f"<b>Confidence:</b> {confidence*100:.2f}%", styles["BodyText"]))
    story.append(Paragraph(f"<b>Severity:</b> {severity}", styles["BodyText"]))

    story.append(Spacer(1, 10))

    cost_text = repair_cost["display"] if repair_cost else "N/A"
    time_text = repair_time["display"] if repair_time else "N/A"

    story.append(
        Paragraph(f"<b>Estimated Repair Cost:</b> {cost_text}", styles["BodyText"])
    )

    story.append(
        Paragraph(f"<b>Estimated Repair Time:</b> {time_text}", styles["BodyText"])
    )

    story.append(Spacer(1, 20))
    story.append(
        Paragraph(
            "<b>Generated Automatically by Surface Crack Detection AI</b>",
            styles["Italic"],
        )
    )

    doc.build(story)

    return filepath