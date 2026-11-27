"""Portable PDF and Word exports of saved screening evidence."""

from collections import defaultdict
from html import escape
from io import BytesIO
from typing import Literal

from docx import Document
from docx.shared import Inches, Mm, Pt, RGBColor
from PIL import Image, ImageOps
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image as PdfImage, KeepTogether, Paragraph, SimpleDocTemplate

from app.schemas.analysis import Analysis
from app.services.report import FIELD_NAMES, KIND_ACTIONS, verified_photos

REPORT_TYPES = {
    "html": "text/html",
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
ADVISORY = "Advisory screening. Verify findings on the physical package."


def _photo(raw: bytes) -> tuple[BytesIO, int, int]:
    with Image.open(BytesIO(raw)) as original:
        image = ImageOps.exif_transpose(original).convert("RGB")
        image.thumbnail((1400, 1400))
        data = BytesIO()
        image.save(data, format="JPEG", quality=88)
    data.seek(0)
    return data, image.width, image.height


def _report_items(record: dict, analysis: Analysis):
    yield "title", record["product_name"]
    yield "body", f'{record["id"]}  |  {record["timestamp"][:10]}'
    outcome = analysis.classification
    yield "heading", outcome.outcome if outcome else record["final_outcome"]
    if outcome:
        yield "body", outcome.reason
    yield "body", ADVISORY
    yield "heading", "Declaration readings"
    for field in analysis.fields:
        name = FIELD_NAMES.get(field.field, field.field)
        sources = ", ".join(dict.fromkeys(item.view.capitalize() for item in field.evidence))
        if field.status == "observed" and field.value and any(char.isalnum() for char in field.value):
            yield "body", f"{name} / {field.value}" + (f" [{sources}]" if sources else "")
        elif field.status == "conflict":
            candidates = ", ".join(dict.fromkeys(f"{item.value} [{item.view}]" for item in field.evidence))
            yield "body", f"{name} / Conflicting readings. {candidates}"
    yield "heading", "Verify on the package"
    review = defaultdict(list)
    flagged = defaultdict(list)
    if analysis.profile.status != "selected":
        yield "body", analysis.profile.reason
    for check in analysis.checks.results if analysis.checks else []:
        name = FIELD_NAMES.get(check.field, check.field)
        if check.status == "fail":
            flagged[check.reason].append(f"{name} ({check.citation})")
        if check.status == "insufficient_evidence":
            review[KIND_ACTIONS[check.kind]].append(name)
    for reason, declarations in flagged.items():
        yield "body", f"{reason} {'; '.join(dict.fromkeys(declarations))}."
    for action, names in review.items():
        yield "body", f"{action}. {', '.join(dict.fromkeys(names))}."
    if not flagged and not review and analysis.profile.status == "selected":
        yield "body", "Compare the readings with the printed declarations."
    yield "heading", "Rule profile and sources"
    profile = analysis.profile
    yield "body", f"{profile.id or 'Pending profile'} {profile.version or ''} | {profile.inputs.as_of} | {profile.inputs.origin}"
    for citation, url in dict.fromkeys((rule.citation, rule.source_url) for rule in profile.rules):
        yield "body", f"{citation} / {url}"
    yield "heading", "Package photos"
    for view, photo, raw, file_hash in verified_photos(record, analysis):
        filename = photo.get("original_filename") or photo.get("filename") or ""
        yield "photo_label", f"{view.capitalize()} view / {filename}"
        yield "image", _photo(raw)
        yield "caption", f"Original SHA-256 {file_hash}"


def export_report(record: dict, analysis: Analysis, format: Literal["pdf", "docx"]) -> bytes:
    output = BytesIO()
    items = _report_items(record, analysis)
    if format == "docx":
        doc = Document()
        doc.core_properties.title = f'Nirikshak-LM / {record["id"]}'
        section = doc.sections[0]
        section.page_width, section.page_height = Mm(210), Mm(297)
        section.left_margin = section.right_margin = Mm(17)
        section.top_margin = section.bottom_margin = Mm(18)
        section.header.paragraphs[0].text = "NIRIKSHAK-LM  /  PACKAGE SCREENING"
        section.footer.paragraphs[0].text = record["id"]
        normal = doc.styles["Normal"]
        normal.font.name, normal.font.size, normal.font.color.rgb = "Arial", Pt(10), RGBColor.from_string("172D35")
        normal.paragraph_format.space_after = Pt(4)
        normal.paragraph_format.line_spacing = 1.08
        for kind, item in items:
            if kind == "image":
                data, width, height = item
                doc.add_picture(data, width=Inches(min(5.4, width / height * 2.0)))
                doc.paragraphs[-1].paragraph_format.keep_with_next = True
            elif kind in ("title", "heading"):
                doc.add_heading(item, level=0 if kind == "title" else 1)
            else:
                paragraph = doc.add_paragraph(item, style="Caption" if kind == "caption" else "Normal")
                if kind == "photo_label":
                    paragraph.paragraph_format.keep_with_next = True
        doc.save(output)
    else:
        pdfmetrics.registerFont(TTFont("ReportVera", "Vera.ttf"))
        pdfmetrics.registerFont(TTFont("ReportVeraBold", "VeraBd.ttf"))
        ink = HexColor("#172d35")
        body = ParagraphStyle("Body", fontName="ReportVera", fontSize=9.5, leading=14,
                              spaceAfter=5, textColor=ink, alignment=TA_LEFT, wordWrap="LTR")
        styles = {
            "body": body,
            "photo_label": ParagraphStyle("PhotoLabel", parent=body, keepWithNext=True),
            "caption": ParagraphStyle("Caption", parent=body, fontSize=8, leading=11),
            "title": ParagraphStyle("Title", parent=body, fontName="ReportVeraBold",
                                    fontSize=23, leading=27, keepWithNext=True),
            "heading": ParagraphStyle("Heading", parent=body, fontName="ReportVeraBold",
                                      fontSize=13, leading=18, spaceBefore=10, keepWithNext=True),
        }
        story = []
        for kind, item in items:
            if kind == "image":
                data, width, height = item
                scale = min(370 / width, 144 / height)
                story.append(PdfImage(data, width * scale, height * scale, hAlign="LEFT"))
            elif kind == "caption":
                label, photo = story[-2:]
                del story[-2:]
                story.append(KeepTogether([label, photo, Paragraph(escape(item), styles[kind])]))
            else:
                story.append(Paragraph(escape(item.replace("₹", "INR ")).replace("\n", "<br/>"), styles[kind]))

        def furniture(canvas, doc):
            canvas.setFillColor(ink)
            canvas.setFont("ReportVera", 8)
            canvas.drawString(44, A4[1] - 35, "NIRIKSHAK-LM  /  PACKAGE SCREENING")
            canvas.drawString(44, 29, record["id"])
            canvas.drawRightString(A4[0] - 44, 29, f"Page {doc.page}")

        SimpleDocTemplate(output, pagesize=A4, title=f'Nirikshak-LM / {record["id"]}',
                          leftMargin=44, rightMargin=44, topMargin=56, bottomMargin=47).build(
                              story, onFirstPage=furniture, onLaterPages=furniture)
    return output.getvalue()
