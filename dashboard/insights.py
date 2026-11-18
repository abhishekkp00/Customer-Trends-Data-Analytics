"""Insights and recommendations tab."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from analytics.insights import Insight, generate_insights


def render(df: pd.DataFrame) -> None:
    st.caption("Generated live from the current filters. Findings with too little data are not shown.")
    for insight in generate_insights(df):
        st.markdown(_insight_html(insight), unsafe_allow_html=True)


def _insight_html(insight: Insight) -> str:
    if not insight.supported:
        return f'<div class="insight"><h4>{insight.title}</h4><p>ℹ️ {insight.message}</p></div>'
    return f"""<div class="insight"><h4>{insight.title}</h4>
            <p><span class="lbl">What the data shows:</span> {insight.finding}</p>
            <p><span class="lbl">Metric &amp; comparison:</span> {insight.metric}</p>
            <p><span class="lbl">Why it matters:</span> {insight.why_it_matters}</p>
            <p><span class="lbl">Recommendation:</span> {insight.recommendation}</p>
            <p><span class="lbl">Caveat:</span> {insight.caveat}</p></div>"""
