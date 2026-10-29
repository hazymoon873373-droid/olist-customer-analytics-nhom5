from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
import os

import pandas as pd
import streamlit as st

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    LongTable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    TableStyle,
)


def load_pdf_font():
    base_dir = Path(__file__).resolve().parent

    # Ưu tiên font đặt trong dự án.
    # Nếu chưa có, dùng Arial trên máy Windows.
    candidates = [
        base_dir / "assets" / "fonts" / "IBMPlexSans-400.ttf",
        base_dir / "assets" / "fonts" / "Arial.ttf",
        Path(os.environ.get("WINDIR", "C:/Windows"))
        / "Fonts"
        / "arial.ttf",
    ]

    for font_path in candidates:
        if font_path.exists():
            font_name = "OlistVietnamese"

            if font_name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(
                    TTFont(font_name, str(font_path))
                )

            return font_name

    raise FileNotFoundError(
        "Không tìm thấy font tiếng Việt. "
        "Đặt file Arial.ttf vào assets/fonts trong dự án."
    )


def create_pdf(data, filters, title, username, columns):
    font_name = load_pdf_font()
    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=title,
        author=username,
    )

    title_style = ParagraphStyle(
        "ReportTitle",
        fontName=font_name,
        fontSize=18,
        leading=24,
        textColor=colors.HexColor("#1D4ED8"),
        spaceAfter=12,
    )

    body_style = ParagraphStyle(
        "ReportBody",
        fontName=font_name,
        fontSize=9,
        leading=13,
        spaceAfter=5,
    )

    cell_style = ParagraphStyle(
        "ReportCell",
        fontName=font_name,
        fontSize=8,
        leading=11,
        splitLongWords=True,
    )

    header_style = ParagraphStyle(
        "ReportHeader",
        parent=cell_style,
        textColor=colors.white,
    )

    def paragraph(value, style):
        return Paragraph(
            escape(str(value)).replace("\n", "<br/>"),
            style,
        )

    now = datetime.now(
        timezone(timedelta(hours=7))
    ).strftime("%d/%m/%Y %H:%M:%S")

    preview = data.head(100)

    story = [
        paragraph(title, title_style),
        paragraph(
            f"Nguồn: Olist Brazil | Đơn vị tiền: BRL",
            body_style,
        ),
        paragraph(
            f"Người xuất: {username} | "
            f"Thời điểm tạo (UTC+7): {now}",
            body_style,
        ),
        paragraph(
            f"Tổng kết quả phù hợp: {len(data):,} dòng. "
            f"Bảng PDF hiển thị {len(preview):,} dòng đầu "
            f"theo thứ tự hiện tại; không phải danh sách xếp hạng.",
            body_style,
        ),
        paragraph(
            "Dùng CSV/Excel để tải toàn bộ kết quả.",
            body_style,
        ),
        Spacer(1, 5 * mm),
    ]

    for name, value in filters.items():
        story.append(
            paragraph(f"{name}: {value}", body_style)
        )

    story.append(Spacer(1, 5 * mm))

    selected_columns = [
        column
        for column in columns
        if column in data.columns
    ]

    if not selected_columns:
        raise ValueError("Không có cột phù hợp để xuất PDF.")

    table_data = [
        [
            paragraph(columns[column], header_style)
            for column in selected_columns
        ]
    ]

    for row in preview[selected_columns].itertuples(
        index=False,
        name=None,
    ):
        cells = []

        for value in row:
            if pd.isna(value):
                text = "—"
            elif isinstance(value, (float,)):
                text = f"{value:,.2f}"
            else:
                text = str(value)

            cells.append(paragraph(text, cell_style))

        table_data.append(cells)

    table = LongTable(
        table_data,
        colWidths=[
            document.width / len(selected_columns)
        ] * len(selected_columns),
        repeatRows=1,
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#1D4ED8"),
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#EFF6FF")],
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.3,
                    colors.HexColor("#CBD5E1"),
                ),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )

    story.append(table)

    def add_page_number(canvas, doc):
        canvas.saveState()
        canvas.setFont(font_name, 8)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawRightString(
            doc.pagesize[0] - 15 * mm,
            8 * mm,
            f"Trang {doc.page}",
        )
        canvas.restoreState()

    document.build(
        story,
        onFirstPage=add_page_number,
        onLaterPages=add_page_number,
    )

    return buffer.getvalue()


def render_pdf_export(
    data,
    filters,
    title,
    username,
    columns,
    file_name,
    key,
):
    if data.empty:
        return

    if st.button(
        "Chuẩn bị PDF — tối đa 100 dòng",
        key=f"{key}_prepare",
    ):
        try:
            with st.spinner("Đang tạo PDF..."):
                pdf_bytes = create_pdf(
                    data=data,
                    filters=filters,
                    title=title,
                    username=username,
                    columns=columns,
                )
        except Exception as error:
            st.error(f"Không tạo được PDF: {error}")
            return

        st.download_button(
            label="Tải báo cáo PDF",
            data=pdf_bytes,
            file_name=file_name,
            mime="application/pdf",
            key=f"{key}_download",
        )

        st.caption(
            "Sau khi thay đổi bộ lọc, hãy chuẩn bị PDF mới."
        )
