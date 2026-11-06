"""
SecAI Profesyonel Siber Güvenlik ve Vaka Defteri PDF Raporlama Motoru.

Vaka Defteri kayıtlarını ve penetrasyon testi/denetim bulgularını şirketlere,
yöneticilere ve denetçilere doğrudan sunulabilecek kurumsal standartlarda
(Executive Summary, Scope, Findings, Risk Matrix, Hardening Checklist, Sign-off)
PDF raporlarına dönüştürür.
"""

from datetime import datetime
from pathlib import Path
import re
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from secai.config import get_export_dir
from secai.core.database import get_chat_history, get_note, get_user_profile


class NumberedCanvas(canvas.Canvas):
    """Her sayfaya kurumsal üst bilgi, alt bilgi ve dinamik sayfa numarası ekler."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages: int):
        self.saveState()
        page_w, page_h = A4

        # Üst Bilgi (Header)
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#0284c7"))
        self.drawString(36, page_h - 24, "SecAI CYBER DEFENSE INTELLIGENCE")
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        self.drawRightString(page_w - 36, page_h - 24, "TLP:AMBER | GİZLİ - KURUMSAL DEĞERLENDİRME")
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(36, page_h - 28, page_w - 36, page_h - 28)

        # Alt Bilgi (Footer)
        self.line(36, 32, page_w - 36, 32)
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        self.drawString(36, 20, "Hazırlayan: SecAI Autonomous Cyber Engine & Lead Security Analyst")
        page_str = f"Sayfa {self._pageNumber} / {total_pages}"
        self.drawRightString(page_w - 36, 20, page_str)
        self.restoreState()


def _clean_md_inline(text: str) -> str:
    s = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = re.sub(r"`([^`]+)`", r"<font name='Courier'>\1</font>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", s)
    return s


def _parse_markdown_to_flowables(text: str, styles: dict) -> list:
    """Markdown metnini ReportLab flowable öğelerine (başlık, paragraf, tablo, kod bloğu) ayrıştırır."""
    flowables = []
    lines = text.strip().split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]

        # Boş satır
        if not line.strip():
            flowables.append(Spacer(1, 6))
            i += 1
            continue

        # Kod Bloğu
        if line.strip().startswith("```"):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # Kapanış ``` geç
            code_text = "\n".join(code_lines).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            code_html = f"<font name='Courier' size='8' color='#e2e8f0'>{code_text.replace(chr(10), '<br/>')}</font>"
            t = Table(
                [[Paragraph(code_html, styles["CodeBlock"])]],
                colWidths=[A4[0] - 72],
            )
            t.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0f172a")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#334155")),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ])
            )
            flowables.append(Spacer(1, 4))
            flowables.append(t)
            flowables.append(Spacer(1, 8))
            continue

        # Başlıklar
        if line.startswith("# "):
            h_text = _clean_md_inline(line[2:].strip())
            flowables.append(Spacer(1, 10))
            flowables.append(Paragraph(f"<b>{h_text}</b>", styles["Heading1"]))
            flowables.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0284c7"), spaceAfter=8))
            i += 1
            continue
        if line.startswith("## "):
            h_text = _clean_md_inline(line[3:].strip())
            flowables.append(Spacer(1, 8))
            flowables.append(Paragraph(f"<b>{h_text}</b>", styles["Heading2"]))
            flowables.append(Spacer(1, 4))
            i += 1
            continue
        if line.startswith("### "):
            h_text = _clean_md_inline(line[4:].strip())
            flowables.append(Spacer(1, 6))
            flowables.append(Paragraph(f"<b>{h_text}</b>", styles["Heading3"]))
            flowables.append(Spacer(1, 3))
            i += 1
            continue

        # Tablo satırları
        if line.strip().startswith("|") and line.strip().endswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                if not re.match(r"^\|[\s:\-|]+\|$", lines[i].strip()):
                    table_lines.append(lines[i].strip())
                i += 1
            if table_lines:
                table_data = []
                for t_l in table_lines:
                    cols = [c.strip() for c in t_l.split("|")[1:-1]]
                    row_cells = []
                    for c in cols:
                        clean_c = _clean_md_inline(c)
                        cell_p = Paragraph(f"<b>{clean_c}</b>" if len(table_data) == 0 else clean_c, styles["Body"])
                        row_cells.append(cell_p)
                    table_data.append(row_cells)

                if table_data:
                    num_cols = max(len(r) for r in table_data)
                    col_w = (A4[0] - 72) / max(1, num_cols)
                    t_flowable = Table(table_data, colWidths=[col_w] * num_cols)
                    t_flowable.setStyle(
                        TableStyle([
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
                            ("TOPPADDING", (0, 0), (-1, -1), 4),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ])
                    )
                    flowables.append(Spacer(1, 6))
                    flowables.append(t_flowable)
                    flowables.append(Spacer(1, 8))
            continue

        # Liste maddeleri
        if line.strip().startswith(("- ", "* ", "• ")):
            item_text = line.strip()[2:].strip()
            item_html = f"• {_clean_md_inline(item_text)}"
            flowables.append(Paragraph(item_html, styles["BulletItem"]))
            i += 1
            continue

        # Standart Paragraf
        p_html = _clean_md_inline(line.strip())
        flowables.append(Paragraph(p_html, styles["Body"]))
        i += 1

    return flowables


def generate_custom_pdf_report(
    title: str,
    content: str,
    category: str = "secops",
    tags: str = "audit, report",
    note_id: Optional[int] = None,
    created_at: Optional[str] = None,
    output_path: Optional[Path] = None,
) -> Path:
    """Kurumsal standartlarda tam biçimlendirilmiş profesyonel bir siber güvenlik PDF raporu üretir."""
    user_profile = get_user_profile() or "Kayra Divrik (Lead SecOps Analyst)"

    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", title.lower()).strip("_") or "report"
    ref_id = f"#SEC-2026-N{note_id:04d}" if note_id else f"#SEC-2026-{datetime.now().strftime('%m%d%H%M')}"

    if output_path:
        target = output_path.expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
    else:
        prefix = f"secai_report_{note_id}_" if note_id else "secai_audit_report_"
        target = get_export_dir() / f"{prefix}{slug}.pdf"

    doc = SimpleDocTemplate(
        str(target),
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=46,
        bottomMargin=46,
    )

    base_styles = getSampleStyleSheet()

    styles = {
        "Title": ParagraphStyle(
            "SecTitle",
            parent=base_styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#0f172a"),
            alignment=0,
            spaceAfter=4,
        ),
        "Subtitle": ParagraphStyle(
            "SecSubTitle",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#0284c7"),
            spaceAfter=12,
        ),
        "Heading1": ParagraphStyle(
            "SecH1",
            parent=base_styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=10,
            spaceAfter=4,
        ),
        "Heading2": ParagraphStyle(
            "SecH2",
            parent=base_styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=8,
            spaceAfter=3,
        ),
        "Heading3": ParagraphStyle(
            "SecH3",
            parent=base_styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#334155"),
            spaceBefore=6,
            spaceAfter=2,
        ),
        "Body": ParagraphStyle(
            "SecBody",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#1e293b"),
            spaceAfter=5,
        ),
        "BulletItem": ParagraphStyle(
            "SecBullet",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#1e293b"),
            leftIndent=12,
            spaceAfter=3,
        ),
        "CodeBlock": ParagraphStyle(
            "SecCode",
            parent=base_styles["Normal"],
            fontName="Courier",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#e2e8f0"),
        ),
        "MetaCell": ParagraphStyle(
            "SecMeta",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#334155"),
        ),
    }

    story = []

    # 1. Başlık & Kurumsal Banner
    story.append(Paragraph("SİBER GÜVENLİK DEĞERLENDİRME & VAKA RAPORU", styles["Title"]))
    story.append(
        Paragraph("AUTONOMOUS SECURITY ASSESSMENT & INCIDENT INVESTIGATION REPORT", styles["Subtitle"])
    )

    # 2. Üst Metadata Tablosu
    now_str = created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    analyst_name = user_profile.split(".")[0][:45] if user_profile else "Kayra Divrik"
    meta_rows = [
        [
            Paragraph(f"<b>Rapor Referans No:</b> {ref_id}", styles["MetaCell"]),
            Paragraph(f"<b>Tarih / Saat:</b> {now_str}", styles["MetaCell"]),
        ],
        [
            Paragraph(f"<b>Vaka Başlığı:</b> {title}", styles["MetaCell"]),
            Paragraph(f"<b>Kategori:</b> <font color='#0284c7'><b>{category.upper()}</b></font>", styles["MetaCell"]),
        ],
        [
            Paragraph(f"<b>Güvenlik Analisti:</b> {analyst_name}", styles["MetaCell"]),
            Paragraph(f"<b>İnceleme Motoru:</b> SecAI v0.9.0 & RTX Telemetri", styles["MetaCell"]),
        ],
        [
            Paragraph(f"<b>Etiketler / Kapsam:</b> {tags}", styles["MetaCell"]),
            Paragraph("<b>Sınıflandırma:</b> <font color='#dc2626'><b>TLP:AMBER (GİZLİ)</b></font>", styles["MetaCell"]),
        ],
    ]
    meta_table = Table(meta_rows, colWidths=[(A4[0] - 72) * 0.55, (A4[0] - 72) * 0.45])
    meta_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    story.append(meta_table)
    story.append(Spacer(1, 14))

    # 3. Yönetici Özeti (Executive Callout Box)
    summary_text = (
        "<b>YÖNETİCİ ÖZETİ (EXECUTIVE SUMMARY):</b><br/>"
        "İşbu rapor, SecAI Güvenlik Operasyonları Motoru tarafından yerel ve ağ seviyesindeki "
        "telemetri, zafiyet tarama bulguları ve vaka kayıtları incelenerek oluşturulmuştur. "
        "Tespit edilen risk faktörleri, zafiyet kanıtları ve uygulanması önerilen sıkılaştırma "
        "adımları aşağıda teknik detaylarıyla belgelenmiştir."
    )
    exec_table = Table([[Paragraph(summary_text, styles["Body"])]], colWidths=[A4[0] - 72])
    exec_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0fdf4")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#86efac")),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    story.append(exec_table)
    story.append(Spacer(1, 12))

    # 4. Rapor İçeriği (Markdown Flowables)
    body_flowables = _parse_markdown_to_flowables(content, styles)
    story.extend(body_flowables)

    # 5. Resmi Onay & İmza Bloğu (Sign-Off Block)
    story.append(Spacer(1, 20))
    sign_rows = [
        [
            Paragraph("<b>DENETLEYEN GÜVENLİK ANALİSTİ</b><br/><br/>İmza: ___________________________<br/>Tarih: " + now_str[:10], styles["MetaCell"]),
            Paragraph("<b>DİJİTAL SİBER ONAY & DOĞRULAMA</b><br/><br/>SecAI Autonomous Engine v0.9.0<br/>Status: <b>VERIFIED & AUDITED</b>", styles["MetaCell"]),
        ]
    ]
    sign_table = Table(sign_rows, colWidths=[(A4[0] - 72) * 0.5, (A4[0] - 72) * 0.5])
    sign_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ])
    )
    story.append(KeepTogether([sign_table]))

    doc.build(story, canvasmaker=NumberedCanvas)
    return target


def generate_note_pdf_report(note_id: int, output_path: Optional[Path] = None) -> Path:
    """Belirtilen Vaka Defteri (#ID) notundan kurumsal bir Siber Güvenlik Değerlendirme PDF'i üretir."""
    raw_note = get_note(note_id)
    if not raw_note:
        raise ValueError(f"#{note_id} numaralı vaka kaydı bulunamadı.")
    note = dict(raw_note)

    return generate_custom_pdf_report(
        title=note["title"],
        content=note["content"],
        category=note.get("category", "secops"),
        tags=note.get("tags", "secops, audit"),
        note_id=note["id"],
        created_at=note.get("created_at"),
        output_path=output_path,
    )


def generate_session_pdf_report(session_id: str, output_path: Optional[Path] = None) -> Path:
    """Oturumdaki tespitlerden ve mesajlaşma geçmişinden resmi bir SecOps değerlendirme PDF raporu üretir."""
    history = get_chat_history(session_id=session_id, limit=60)
    if not history:
        raise ValueError(f"Oturumda ({session_id}) raporlanacak mesaj kaydı bulunamadı.")

    content_parts = []
    for m in history:
        role_label = "Kullanıcı / Denetçi" if m["role"] == "user" else "SecAI Güvenlik Analisti"
        content_parts.append(f"### {role_label}\n{m['content']}\n")

    full_content = "\n\n".join(content_parts)
    return generate_custom_pdf_report(
        title=f"SecOps Oturum Raporu ({session_id})",
        content=full_content,
        category="secops",
        tags=f"session-{session_id}, chat-audit",
        output_path=output_path,
    )
