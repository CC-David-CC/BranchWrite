from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def build():
    doc = SimpleDocTemplate(
        "document.pdf",
        pagesize=letter,
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
        topMargin=0.85 * inch,
        bottomMargin=0.85 * inch,
        title="Caring for a Dog",
        author="BranchWrite",
    )

    styles = getSampleStyleSheet()
    heading_style = ParagraphStyle(
        "BigHeading",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        spaceAfter=14,
        textColor=colors.HexColor("#1F3A5F"),
        alignment=TA_LEFT,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=12,
        leading=16,
        spaceAfter=10,
    )
    cell_style = ParagraphStyle(
        "Cell",
        parent=body_style,
        fontSize=11,
        leading=14,
        spaceAfter=0,
    )
    header_style = ParagraphStyle(
        "HeaderCell",
        parent=cell_style,
        fontName="Helvetica-Bold",
    )
    note_style = ParagraphStyle(
        "Note",
        parent=body_style,
        fontName="Helvetica-Oblique",
        textColor=colors.HexColor("#444444"),
    )

    def add_page_number(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 10)
        canvas.setFillColor(colors.HexColor("#555555"))
        canvas.drawCentredString(letter[0] / 2.0, 0.45 * inch, f"Page {doc.page}")
        canvas.restoreState()

    story = []

    story.append(Paragraph("Daily Care", heading_style))
    story.append(
        Paragraph(
            "A dog needs predictable routines and basic comforts every day. "
            "The essentials below are simple to track and easy to adjust as "
            "your dog grows or its activity changes.",
            body_style,
        )
    )
    story.append(Spacer(1, 8))

    table_data = [
        [Paragraph("Need", header_style), Paragraph("Guidance", header_style)],
        [
            Paragraph("Food", cell_style),
            Paragraph(
                "Offer measured meals at consistent times and choose food suited "
                "to age, size and health.",
                cell_style,
            ),
        ],
        [
            Paragraph("Water", cell_style),
            Paragraph(
                "Keep fresh water available and rinse bowls daily.",
                cell_style,
            ),
        ],
        [
            Paragraph("Walks", cell_style),
            Paragraph(
                "Provide daily exercise and sniffing time, adjusted for weather, "
                "age and fitness.",
                cell_style,
            ),
        ],
        [
            Paragraph("Rest", cell_style),
            Paragraph(
                "Give a quiet, comfortable place to sleep away from traffic and noise.",
                cell_style,
            ),
        ],
    ]

    table = Table(table_data, colWidths=[1.3 * inch, 5.5 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9EAD3")),
                ("GRID", (0, 0), (-1, -1), 0.75, colors.HexColor("#7F7F7F")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(table)

    story.append(PageBreak())

    story.append(Paragraph("A Safe Home", heading_style))
    story.append(
        Paragraph(
            "Use this short checklist to keep the household comfortable and low-risk.",
            body_style,
        )
    )

    checklist = [
        "Fresh water and food bowls are clean and stable.",
        "The dog has a safe resting area away from hazards.",
        "Toxic plants, chemicals, cords and small swallowable objects are out of reach.",
        "Windows, gates and doors are secure when needed.",
        "Identification, leash and collar are ready for outings.",
    ]
    for item in checklist:
        story.append(Paragraph(f"- {item}", body_style))

    story.append(Spacer(1, 12))
    story.append(
        Paragraph(
            "Note: Ask a veterinarian about medical questions, vaccinations, "
            "diet changes, injuries or unusual behavior.",
            note_style,
        )
    )

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)


if __name__ == "__main__":
    build()
