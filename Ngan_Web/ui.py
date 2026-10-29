"""Presentation helpers for the Olist workspace."""
import base64
from html import escape
from pathlib import Path

import streamlit as st


def load_style():
    root = Path(__file__).resolve().parent
    fonts = []
    for weight in (400, 500, 600):
        encoded = base64.b64encode((root / f'assets/fonts/IBMPlexSans-{weight}.ttf').read_bytes()).decode()
        fonts.append(f"@font-face{{font-family:'IBM Plex Sans';font-style:normal;font-weight:{weight};font-display:swap;src:url(data:font/ttf;base64,{encoded}) format('truetype')}}")
    st.markdown('<style>' + ''.join(fonts) + (root / 'style.css').read_text(encoding='utf8') + '</style>', unsafe_allow_html=True)


def metric_strip(entries):
    cells = ''.join(
        f'<div class="stat"><span>{escape(label)}</span><strong>{escape(str(value))}</strong>'
        f'<small>{escape(note)}</small></div>' for label, value, note in entries
    )
    st.markdown(f'<div class="stat-strip" style="--stat-count:{len(entries)}">{cells}</div>', unsafe_allow_html=True)


def number(value, decimals=0):
    """Use one Vietnamese number convention across the workspace."""
    if value is None:
        return '—'
    return f'{value:,.{decimals}f}'.translate(str.maketrans({',': '.', '.': ','}))


def brand():
    mark = (Path(__file__).resolve().parent / 'assets/olist-mark.svg').read_text(encoding='utf8')
    st.markdown(f'<div class="brand-lockup">{mark}<div><strong>olist<span> / insights</span></strong>'
                '<small>Không gian dữ liệu · Nhóm 5</small></div></div>', unsafe_allow_html=True)


def page_header(title, description, *, scope='Olist Brazil · 2016–2018'):
    st.markdown(f'<header class="page-heading"><div><div class="page-path">Không gian phân tích / Olist</div>'
                f'<h1>{escape(title)}</h1><p>{escape(description)}</p></div>'
                f'<span class="scope-label">{escape(scope)}</span></header>', unsafe_allow_html=True)


def section_heading(title, description=''):
    st.markdown(f'<div class="section-heading"><h3>{escape(title)}</h3>'
                f'<p>{escape(description)}</p></div>', unsafe_allow_html=True)


def insight(title, detail):
    st.markdown(f'<div class="insight-note"><span class="insight-dot" aria-hidden="true"></span>'
                f'<div><strong>{escape(title)}</strong><p>{escape(detail)}</p></div></div>', unsafe_allow_html=True)


def chart_spec(category, value, category_title, value_title, *, temporal=False, height=220, value_format='~s', tooltip_format=',.2f', category_sort='-x'):
    """One hue, straight line, zero baseline, continuous dates and labelled axes."""
    return {
        'mark': {'type': 'line' if temporal else 'bar', 'color': '#1b6c80', 'strokeWidth': 2.5,
                 **({} if temporal else {'cornerRadiusEnd': 3, 'size': 12})},
        'encoding': {
            'x' if temporal else 'y': {
                'field': category, 'type': 'temporal' if temporal else 'nominal',
                'title': category_title, **({} if temporal else {'sort': category_sort}),
                'axis': {'labelAngle': 0, 'labelLimit': 180, **({'tickCount': 5, 'format': '%m/%Y'} if temporal else {})},
            },
            'y' if temporal else 'x': {
                'field': value, 'type': 'quantitative', 'title': value_title,
                'scale': {'zero': True}, 'axis': {'tickCount': 4, 'format': value_format},
            },
            'tooltip': [
                {'field': category, 'title': category_title, 'type': 'temporal' if temporal else 'nominal', **({'format': '%m/%Y'} if temporal else {})},
                {'field': value, 'title': value_title, 'type': 'quantitative', 'format': tooltip_format},
            ],
        },
        'height': height,
        'config': {
            'font': 'IBM Plex Sans', 'background': '#ffffff', 'view': {'stroke': None},
            'axis': {'domain': False, 'ticks': False, 'labelPadding': 8, 'titlePadding': 14, 'gridColor': '#edf1f2', 'labelColor': '#53636b', 'titleColor': '#53636b', 'labelFontSize': 12, 'titleFontSize': 12},
            'axisX': {'grid': not temporal}, 'axisY': {'grid': temporal},
        },
    }


def render_chart(frame, category, value, category_title, value_title, **kwargs):
    st.vega_lite_chart(frame, chart_spec(category, value, category_title, value_title, **kwargs), width='stretch', theme=None)
