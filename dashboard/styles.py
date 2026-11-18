"""Page styling and the small HTML snippets that depend on it."""
from __future__ import annotations

import streamlit as st

CSS = """
<style>
.block-container {padding-top: 1.6rem; max-width: 1500px;}
.hero {background: linear-gradient(120deg,#312E81 0%,#4F46E5 55%,#0EA5E9 100%);
       padding: 1.4rem 1.8rem; border-radius: 16px; color: #fff; margin-bottom: 1rem;}
.hero h1 {font-size: 1.7rem; margin: 0; color: #fff; font-weight: 700; padding: 0;}
.hero p {margin: .35rem 0 0 0; opacity: .9; font-size: .95rem;}
.kpi-card {background: var(--secondary-background-color); border: 1px solid rgba(148,163,184,.35);
           border-left: 5px solid #4F46E5; border-radius: 12px; padding: .85rem 1rem; margin-bottom: .8rem;
           min-height: 138px; transition: transform .15s ease, box-shadow .15s ease;}
.kpi-card:hover {transform: translateY(-2px); box-shadow: 0 6px 18px rgba(79,70,229,.18);}
.kpi-label {font-size: .78rem; text-transform: uppercase; letter-spacing: .05em; opacity: .75; font-weight: 600;}
.kpi-value {font-size: 1.85rem; font-weight: 700; line-height: 1.25; margin: .15rem 0;}
.kpi-help {font-size: .78rem; opacity: .7; line-height: 1.3;}
.kpi-sub {font-size: .74rem; margin-top: .3rem; color: #0EA5E9; font-weight: 600;}
.finding {border-left: 4px solid #F59E0B; background: rgba(245,158,11,.10); padding: .6rem .9rem;
          border-radius: 8px; font-size: .92rem; margin: .2rem 0 1rem 0;}
.insight {border: 1px solid rgba(148,163,184,.35); border-radius: 12px; padding: 1rem 1.2rem; margin-bottom: 1rem;
          background: var(--secondary-background-color);}
.insight h4 {margin: 0 0 .5rem 0;}
.insight .lbl {font-weight: 700; color: #4F46E5;}
.insight p {margin: .25rem 0; font-size: .92rem;}
@media (max-width: 900px) {.hero h1 {font-size: 1.25rem;} .kpi-value {font-size: 1.45rem;} .kpi-card {min-height: 0;}}
</style>
"""


def inject_styles() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def show_hero(title: str, subtitle: str) -> None:
    st.markdown(f'<div class="hero"><h1>{title}</h1><p>{subtitle}</p></div>', unsafe_allow_html=True)


def show_finding(text: str) -> None:
    """Highlighted one-line takeaway under a chart."""
    st.markdown(f'<div class="finding"><b>Key finding:</b> {text}</div>', unsafe_allow_html=True)
