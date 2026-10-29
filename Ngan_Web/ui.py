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
    st.markdown(f'<div class="stat-strip">{cells}</div>', unsafe_allow_html=True)


def chart_spec(category, value, category_title, value_title, *, temporal=False, height=220):
    """One hue, straight line, zero baseline, continuous dates and labelled axes."""
    return {
        'mark': {'type': 'line' if temporal else 'bar', 'color': '#1b6c80', 'strokeWidth': 2},
        'encoding': {
            'x' if temporal else 'y': {
                'field': category, 'type': 'temporal' if temporal else 'nominal',
                'title': category_title, **({} if temporal else {'sort': '-x'}),
                'axis': {'labelAngle': 0, 'labelLimit': 180, **({'tickCount': 5, 'format': '%m/%Y'} if temporal else {})},
            },
            'y' if temporal else 'x': {
                'field': value, 'type': 'quantitative', 'title': value_title,
                'scale': {'zero': True}, 'axis': {'tickCount': 4, 'format': '~s'},
            },
            'tooltip': [
                {'field': category, 'title': category_title, 'type': 'temporal' if temporal else 'nominal', **({'format': '%m/%Y'} if temporal else {})},
                {'field': value, 'title': value_title, 'type': 'quantitative', 'format': ',.2f'},
            ],
        },
        'height': height,
        'config': {
            'font': 'IBM Plex Sans', 'view': {'stroke': None},
            'axis': {'domain': False, 'gridColor': '#e8eaec', 'labelColor': '#5d5f60', 'titleColor': '#5d5f60', 'labelFontSize': 12, 'titleFontSize': 12},
            'axisX': {'grid': not temporal}, 'axisY': {'grid': temporal},
        },
    }


def render_chart(frame, category, value, category_title, value_title, **kwargs):
    st.vega_lite_chart(frame, chart_spec(category, value, category_title, value_title, **kwargs), width='stretch', theme=None)
