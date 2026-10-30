"""Presentation helpers for the Olist workspace."""

import base64
from html import escape
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parent


def is_dark():
    """Read the active Streamlit theme without changing it."""
    return st.context.theme.type == "dark"


def palette():
    """Colors used only for presentation."""
    if is_dark():
        return {
            "ground": "#0d1726",
            "surface": "#162438",
            "surface_soft": "#1b2d43",
            "text": "#e6edf7",
            "muted": "#b0bfd2",
            "border": "#30435b",
            "accent": "#5eead4",
            "tint": "#153b3b",
            "grid": "#2b3d54",
            "chart": "#5eead4",
            "nav": "#0a1321",
            "nav_border": "#293d53",
            "header": "rgba(13, 23, 38, 0.95)",
            "shadow": "0 12px 30px rgba(0, 0, 0, 0.16)",
            "miss_bg": "#493b21",
            "miss_text": "#ffe0a1",
            "correct_bg": "#173d36",
            "correct_text": "#bdf3da",
        }

    return {
        "ground": "#f3f6fb",
        "surface": "#ffffff",
        "surface_soft": "#edf3fa",
        "text": "#172b43",
        "muted": "#52647b",
        "border": "#dbe4ef",
        "accent": "#0f766e",
        "tint": "#e8f6f0",
        "grid": "#e6edf5",
        "chart": "#168d82",
        "nav": "#142a42",
        "nav_border": "#36536c",
        "header": "rgba(243, 246, 251, 0.95)",
        "shadow": "0 12px 30px rgba(24, 44, 66, 0.065)",
        "miss_bg": "#fff5df",
        "miss_text": "#795b20",
        "correct_bg": "#e8f6ef",
        "correct_text": "#205b4c",
    }


@st.cache_data(show_spinner=False)
def encoded_asset(path, modified_ns):
    """Cache asset encoding; refresh when the file changes."""
    return base64.b64encode(Path(path).read_bytes()).decode("ascii")


def asset_base64(path):
    return encoded_asset(str(path), path.stat().st_mtime_ns)


def load_style():
    """Load local fonts, existing assets and theme-aware CSS."""
    font_rules = []

    for weight in (400, 500, 600):
        path = ROOT / f"assets/fonts/IBMPlexSans-{weight}.ttf"

        if path.is_file():
            encoded = asset_base64(path)

            font_rules.append(
                "@font-face{"
                "font-family:'IBM Plex Sans';"
                "font-style:normal;"
                f"font-weight:{weight};"
                "font-display:swap;"
                f"src:url(data:font/ttf;base64,{encoded}) "
                "format('truetype');"
                "}"
            )

    pattern_path = ROOT / "assets/analytics-pattern.svg"

    pattern_rule = ""

    if pattern_path.is_file():
        encoded_pattern = asset_base64(pattern_path)

        pattern_rule = (
            ':root{--analytics-pattern:'
            f'url("data:image/svg+xml;base64,{encoded_pattern}");'
            "}"
        )

    colors = palette()

    variables = "".join(
        f"--{name.replace('_', '-')}:{value};"
        for name, value in colors.items()
    )

    # The selected theme is read from Streamlit, not changed here.
    theme_rules = (
        f":root{{{variables}}}"
        f".stApp{{color-scheme:{'dark' if is_dark() else 'light'};}}"
    )

    stylesheet = (ROOT / "style.css").read_text(encoding="utf8")

    st.markdown(
        "<style>"
        + "".join(font_rules)
        + pattern_rule
        + stylesheet
        + theme_rules
        + "</style>",
        unsafe_allow_html=True,
    )


def metric_icon(label):
    """Decorative icon; does not change the metric definition."""
    text = str(label).lower()

    if "gmv" in text or "doanh" in text:
        return "💰"

    if "trung bình" in text or "aov" in text:
        return "💎"

    if "đơn" in text:
        return "📦"

    if "rfm" in text or "cụm" in text:
        return "🎯"

    if "chưa" in text or "ngoài" in text:
        return "◌"

    if "mô hình" in text or "điểm" in text:
        return "✦"

    if "khách" in text:
        return "👥"

    return "◈"


def metric_strip(entries):
    cells = []

    for label, value, note in entries:
        cells.append(
            '<div class="stat">'
            '<div class="stat-top">'
            f'<span class="stat-label">{escape(str(label))}</span>'
            '<span class="stat-icon" aria-hidden="true">'
            f'{metric_icon(label)}'
            '</span>'
            '</div>'
            f'<strong>{escape(str(value))}</strong>'
            f'<small>{escape(str(note))}</small>'
            '</div>'
        )

    st.markdown(
        '<div class="stat-strip" '
        f'style="--stat-count:{len(entries)}">'
        + "".join(cells)
        + "</div>",
        unsafe_allow_html=True,
    )


def number(value, decimals=0):
    """Use one Vietnamese number convention across the workspace."""
    if value is None:
        return "—"

    return f"{value:,.{decimals}f}".translate(
        str.maketrans({",": ".", ".": ","})
    )


def brand():
    mark = (ROOT / "assets/olist-mark.svg").read_text(
        encoding="utf8"
    )

    st.markdown(
        '<div class="brand-lockup">'
        f'<div class="brand-symbol">{mark}</div>'
        '<div>'
        '<strong>olist<span> / insights</span></strong>'
        '<small>Không gian dữ liệu · Nhóm 5</small>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def page_header(
    title,
    description,
    *,
    scope="Olist Brazil · 2016–2018",
):
    st.markdown(
        '<header class="page-heading">'
        '<div class="page-heading-content">'
        '<div class="page-path">'
        '<span aria-hidden="true">✦</span> '
        'KHÔNG GIAN PHÂN TÍCH / OLIST'
        '</div>'
        f'<h1>{escape(str(title))}</h1>'
        f'<p>{escape(str(description))}</p>'
        '</div>'
        f'<span class="scope-label">{escape(str(scope))}</span>'
        '</header>',
        unsafe_allow_html=True,
    )


def section_heading(title, description=""):
    st.markdown(
        '<div class="section-heading">'
        f'<h3>{escape(str(title))}</h3>'
        f'<p>{escape(str(description))}</p>'
        '</div>',
        unsafe_allow_html=True,
    )


def insight(title, detail):
    st.markdown(
        '<div class="insight-note">'
        '<span class="insight-dot" aria-hidden="true"></span>'
        '<div>'
        f'<strong>{escape(str(title))}</strong>'
        f'<p>{escape(str(detail))}</p>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def chart_spec(
    category,
    value,
    category_title,
    value_title,
    *,
    temporal=False,
    height=220,
    value_format="~s",
    tooltip_format=",.2f",
    category_sort="-x",
):
    """Theme-aware presentation; preserve fields and scales."""
    colors = palette()

    return {
        "mark": {
            "type": "line" if temporal else "bar",
            "color": colors["chart"],
            "strokeWidth": 2.8,
            **(
                {}
                if temporal
                else {
                    "cornerRadiusEnd": 4,
                    "size": 13,
                }
            ),
        },
        "encoding": {
            "x" if temporal else "y": {
                "field": category,
                "type": "temporal" if temporal else "nominal",
                "title": category_title,
                **({} if temporal else {"sort": category_sort}),
                "axis": {
                    "labelAngle": 0,
                    "labelLimit": 180,
                    **(
                        {
                            "tickCount": 5,
                            "format": "%m/%Y",
                        }
                        if temporal
                        else {}
                    ),
                },
            },
            "y" if temporal else "x": {
                "field": value,
                "type": "quantitative",
                "title": value_title,
                "scale": {"zero": True},
                "axis": {
                    "tickCount": 4,
                    "format": value_format,
                },
            },
            "tooltip": [
                {
                    "field": category,
                    "title": category_title,
                    "type": (
                        "temporal" if temporal else "nominal"
                    ),
                    **(
                        {"format": "%m/%Y"}
                        if temporal
                        else {}
                    ),
                },
                {
                    "field": value,
                    "title": value_title,
                    "type": "quantitative",
                    "format": tooltip_format,
                },
            ],
        },
        "height": height,
        "config": {
            "font": "IBM Plex Sans",
            "background": colors["surface"],
            "view": {"stroke": None},
            "axis": {
                "domain": False,
                "ticks": False,
                "labelPadding": 8,
                "titlePadding": 14,
                "gridColor": colors["grid"],
                "labelColor": colors["muted"],
                "titleColor": colors["muted"],
                "labelFontSize": 12,
                "titleFontSize": 12,
            },
            "legend": {
                "labelColor": colors["muted"],
                "titleColor": colors["text"],
            },
            "axisX": {"grid": not temporal},
            "axisY": {"grid": temporal},
        },
    }


def render_chart(
    frame,
    category,
    value,
    category_title,
    value_title,
    **kwargs,
):
    st.vega_lite_chart(
        frame,
        chart_spec(
            category,
            value,
            category_title,
            value_title,
            **kwargs,
        ),
        width="stretch",
        theme=None,
    )
    