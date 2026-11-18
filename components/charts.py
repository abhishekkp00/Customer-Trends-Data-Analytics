"""Plotly figure builders. Each function answers one business question and
takes already-aggregated data (from analytics.metrics) so it stays testable."""
from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config import settings

COLORS = settings.CATEGORY_COLORS
P = settings.PALETTE
FONT = "Inter, Segoe UI, Roboto, sans-serif"


def _style(fig: go.Figure, title: str, height: int = 380, legend: bool = True) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0.0, xanchor="left", font=dict(size=15)),
        font=dict(family=FONT, size=12),
        height=height,
        margin=dict(l=10, r=10, t=55, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, x=0),
        hoverlabel=dict(font_size=12),
        colorway=COLORS,
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(148,163,184,0.25)", zeroline=False)
    fig.update_yaxes(showgrid=False, zeroline=False)
    return fig


def empty_figure(message: str = "No data for the current filters", height: int = 300) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, font=dict(size=14, color=P["muted"]))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      margin=dict(l=10, r=10, t=10, b=10))
    return fig


def hbar(df: pd.DataFrame, x: str, y: str, title: str, x_label: str, y_label: str = "",
         fmt: str = ",.0f", prefix: str = "", suffix: str = "", color: Optional[str] = None,
         hover_cols: Optional[dict[str, str]] = None, height: Optional[int] = None,
         ascending_top: bool = True) -> go.Figure:
    """Horizontal bar, largest value on top."""
    if df.empty:
        return empty_figure()
    d = df.sort_values(x, ascending=True)  # plotly draws first row at the bottom
    hover = {x: False, y: False}
    custom = None
    template = f"<b>%{{y}}</b><br>{x_label}: {prefix}%{{x:{fmt}}}{suffix}"
    if hover_cols:
        custom = d[list(hover_cols)].to_numpy()
        for i, label in enumerate(hover_cols.values()):
            template += f"<br>{label}: %{{customdata[{i}]:,.1f}}"
    template += "<extra></extra>"
    fig = go.Figure(go.Bar(
        x=d[x], y=d[y], orientation="h",
        marker_color=color or P["primary"],
        text=d[x], texttemplate=f"{prefix}%{{text:{fmt}}}{suffix}", textposition="outside",
        cliponaxis=False, customdata=custom, hovertemplate=template,
    ))
    fig.update_xaxes(title=x_label, tickprefix=prefix, ticksuffix=suffix)
    fig.update_yaxes(title=y_label, automargin=True)
    h = height or max(300, 28 * len(d) + 110)
    return _style(fig, title, height=h, legend=False)


def vbar(df: pd.DataFrame, x: str, y: str, title: str, x_label: str, y_label: str,
         fmt: str = ",.0f", prefix: str = "", suffix: str = "", color: Optional[str] = None,
         height: int = 360) -> go.Figure:
    if df.empty:
        return empty_figure()
    fig = go.Figure(go.Bar(
        x=df[x], y=df[y], marker_color=color or P["primary"],
        text=df[y], texttemplate=f"{prefix}%{{text:{fmt}}}{suffix}", textposition="outside",
        cliponaxis=False,
        hovertemplate=f"<b>%{{x}}</b><br>{y_label}: {prefix}%{{y:{fmt}}}{suffix}<extra></extra>",
    ))
    fig.update_xaxes(title=x_label, showgrid=False, type="category")
    fig.update_yaxes(title=y_label, tickprefix=prefix, ticksuffix=suffix, showgrid=True,
                     gridcolor="rgba(148,163,184,0.25)")
    return _style(fig, title, height=height, legend=False)


def donut(df: pd.DataFrame, names: str, values: str, title: str, value_label: str = "Records",
          height: int = 340) -> go.Figure:
    if df.empty or df[values].sum() == 0:
        return empty_figure()
    fig = go.Figure(go.Pie(
        labels=df[names], values=df[values], hole=0.58, sort=False,
        marker=dict(colors=COLORS, line=dict(color="white", width=2)),
        textinfo="percent", hovertemplate=f"<b>%{{label}}</b><br>{value_label}: %{{value:,.0f}}<br>Share: %{{percent}}<extra></extra>",
    ))
    return _style(fig, title, height=height)


def grouped_bar(df: pd.DataFrame, x: str, y: str, group: str, title: str, y_label: str,
                prefix: str = "", suffix: str = "", fmt: str = ",.0f", height: int = 380,
                category_order: Optional[list[str]] = None) -> go.Figure:
    if df.empty:
        return empty_figure()
    fig = px.bar(df, x=x, y=y, color=group, barmode="group", color_discrete_sequence=COLORS,
                 category_orders={x: category_order} if category_order else None)
    fig.update_traces(hovertemplate=f"<b>%{{x}}</b><br>{group.replace('_', ' ').title()}: %{{fullData.name}}<br>"
                                     f"{y_label}: {prefix}%{{y:{fmt}}}{suffix}<extra></extra>")
    fig.update_xaxes(title="", showgrid=False)
    fig.update_yaxes(title=y_label, tickprefix=prefix, ticksuffix=suffix, showgrid=True,
                     gridcolor="rgba(148,163,184,0.25)")
    return _style(fig, title, height=height)


def treemap(df: pd.DataFrame, path: list[str], values: str, title: str, color: Optional[str] = None,
            height: int = 460) -> go.Figure:
    if df.empty or df[values].sum() <= 0:
        return empty_figure()
    fig = px.treemap(df, path=path, values=values, color=color,
                     color_continuous_scale="Blues" if color else None,
                     color_discrete_sequence=COLORS)
    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>Purchase amount: $%{value:,.0f}<br>"
                      "Share of parent: %{percentParent:.1%}<br>Share of total: %{percentRoot:.1%}<extra></extra>",
        texttemplate="%{label}<br>$%{value:,.0f}", marker=dict(cornerradius=4))
    return _style(fig, title, height=height, legend=False)


def histogram(df: pd.DataFrame, x: str, title: str, x_label: str, color: Optional[str] = None,
              nbins: int = 20, height: int = 340, prefix: str = "") -> go.Figure:
    if df.empty:
        return empty_figure()
    fig = px.histogram(df, x=x, color=color, nbins=nbins, barmode="overlay", opacity=0.75,
                       color_discrete_sequence=COLORS)
    fig.update_traces(hovertemplate=f"{x_label}: {prefix}%{{x}}<br>Records: %{{y}}<extra></extra>")
    fig.update_xaxes(title=x_label, tickprefix=prefix, showgrid=False)
    fig.update_yaxes(title="Records", showgrid=True, gridcolor="rgba(148,163,184,0.25)")
    return _style(fig, title, height=height, legend=color is not None)


def box(df: pd.DataFrame, x: str, y: str, title: str, x_label: str, y_label: str,
        order: Optional[list[str]] = None, prefix: str = "", height: int = 380) -> go.Figure:
    if df.empty:
        return empty_figure()
    fig = px.box(df, x=x, y=y, color=x, color_discrete_sequence=COLORS,
                 category_orders={x: order} if order else None, points=False)
    fig.update_xaxes(title=x_label, showgrid=False)
    fig.update_yaxes(title=y_label, tickprefix=prefix, showgrid=True, gridcolor="rgba(148,163,184,0.25)")
    return _style(fig, title, height=height, legend=False)


def heatmap(pivot: pd.DataFrame, title: str, value_label: str, fmt: str = ",.0f", prefix: str = "",
            x_label: str = "", y_label: str = "", height: int = 400, scale: str = "Blues") -> go.Figure:
    if pivot.empty:
        return empty_figure()
    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=[str(c) for c in pivot.columns], y=[str(i) for i in pivot.index],
        colorscale=scale, colorbar=dict(title=value_label, tickprefix=prefix),
        text=pivot.values, texttemplate=f"{prefix}%{{text:{fmt}}}",
        hovertemplate=f"<b>%{{y}}</b> x <b>%{{x}}</b><br>{value_label}: {prefix}%{{z:{fmt}}}<extra></extra>",
        hoverongaps=False,
    ))
    fig.update_xaxes(title=x_label, showgrid=False)
    fig.update_yaxes(title=y_label, showgrid=False, autorange="reversed")
    return _style(fig, title, height=height, legend=False)


def popularity_scatter(df: pd.DataFrame, title: str, height: int = 460) -> go.Figure:
    """Product popularity (records) vs average rating; bubble = total amount."""
    d = df.dropna(subset=["avg_rating"])
    if d.empty:
        return empty_figure()
    fig = px.scatter(d, x="records", y="avg_rating", size="total_amount", color="category",
                     hover_name="item_purchased", color_discrete_sequence=COLORS, size_max=38,
                     custom_data=["category", "total_amount"])
    fig.update_traces(hovertemplate="<b>%{hovertext}</b><br>Category: %{customdata[0]}<br>"
                                    "Records: %{x:,}<br>Avg rating: %{y:.2f}<br>"
                                    "Total amount: $%{customdata[1]:,.0f}<extra></extra>")
    fig.update_xaxes(title="Purchase records (popularity)", showgrid=True, gridcolor="rgba(148,163,184,0.25)")
    lo, hi = d["avg_rating"].min(), d["avg_rating"].max()
    pad = max(0.05, (hi - lo) * 0.2)
    fig.update_yaxes(title="Average review rating (out of 5)", range=[lo - pad, hi + pad], showgrid=True,
                     gridcolor="rgba(148,163,184,0.25)")
    return _style(fig, title, height=height)
