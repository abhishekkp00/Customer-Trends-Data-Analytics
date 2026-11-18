"""Plotly figure builders. Each function takes already-aggregated data (from
``analytics.metrics``) and returns a styled figure, so the builders stay testable
without Streamlit or a database.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config import settings

COLORS = settings.CATEGORY_COLORS
PRIMARY = settings.PALETTE["primary"]
FONT = "Inter, Segoe UI, Roboto, sans-serif"
GRID_COLOR = "rgba(148,163,184,0.25)"
TRANSPARENT = "rgba(0,0,0,0)"


def show_chart(fig: go.Figure, key: str, container=st) -> None:
    """Render a figure in ``container`` (the page or a column) under an explicit,
    unique key."""
    container.plotly_chart(fig, width="stretch", key=key)


def _style(fig: go.Figure, title: str, height: int = 380, legend: bool = True) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0.0, xanchor="left", font=dict(size=15)),
        font=dict(family=FONT, size=12),
        height=height,
        margin=dict(l=10, r=10, t=55, b=10),
        paper_bgcolor=TRANSPARENT,
        plot_bgcolor=TRANSPARENT,
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, x=0),
        hoverlabel=dict(font_size=12),
        colorway=COLORS,
    )
    fig.update_xaxes(showgrid=True, gridcolor=GRID_COLOR, zeroline=False)
    fig.update_yaxes(showgrid=False, zeroline=False)
    return fig


def empty_figure(message: str = "No data for the current filters", height: int = 300) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, font=dict(size=14, color=settings.PALETTE["muted"]))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(height=height, paper_bgcolor=TRANSPARENT, plot_bgcolor=TRANSPARENT,
                      margin=dict(l=10, r=10, t=10, b=10))
    return fig


def hbar(df: pd.DataFrame, x: str, y: str, title: str, x_label: str, y_label: str = "",
         fmt: str = ",.0f", prefix: str = "", suffix: str = "", color: str | None = None,
         hover_cols: dict[str, str] | None = None, height: int | None = None) -> go.Figure:
    """Horizontal bar with the largest value on top."""
    if df.empty:
        return empty_figure()
    ordered = df.sort_values(x, ascending=True)  # plotly draws the first row at the bottom
    hover_template = f"<b>%{{y}}</b><br>{x_label}: {prefix}%{{x:{fmt}}}{suffix}"
    custom_data = None
    if hover_cols:
        custom_data = ordered[list(hover_cols)].to_numpy()
        for i, label in enumerate(hover_cols.values()):
            hover_template += f"<br>{label}: %{{customdata[{i}]:,.1f}}"
    hover_template += "<extra></extra>"
    fig = go.Figure(go.Bar(
        x=ordered[x], y=ordered[y], orientation="h",
        marker_color=color or PRIMARY,
        text=ordered[x], texttemplate=f"{prefix}%{{text:{fmt}}}{suffix}", textposition="outside",
        cliponaxis=False, customdata=custom_data, hovertemplate=hover_template,
    ))
    fig.update_xaxes(title=x_label, tickprefix=prefix, ticksuffix=suffix)
    fig.update_yaxes(title=y_label, automargin=True)
    return _style(fig, title, height=height or max(300, 28 * len(ordered) + 110), legend=False)


def vbar(df: pd.DataFrame, x: str, y: str, title: str, x_label: str, y_label: str,
         fmt: str = ",.0f", prefix: str = "", suffix: str = "", height: int = 360) -> go.Figure:
    if df.empty:
        return empty_figure()
    fig = go.Figure(go.Bar(
        x=df[x], y=df[y], marker_color=PRIMARY,
        text=df[y], texttemplate=f"{prefix}%{{text:{fmt}}}{suffix}", textposition="outside",
        cliponaxis=False,
        hovertemplate=f"<b>%{{x}}</b><br>{y_label}: {prefix}%{{y:{fmt}}}{suffix}<extra></extra>",
    ))
    fig.update_xaxes(title=x_label, showgrid=False, type="category")
    fig.update_yaxes(title=y_label, tickprefix=prefix, ticksuffix=suffix, showgrid=True, gridcolor=GRID_COLOR)
    return _style(fig, title, height=height, legend=False)


def donut(df: pd.DataFrame, names: str, values: str, title: str, value_label: str = "Records",
          height: int = 340) -> go.Figure:
    if df.empty or df[values].sum() == 0:
        return empty_figure()
    fig = go.Figure(go.Pie(
        labels=df[names], values=df[values], hole=0.58, sort=False,
        marker=dict(colors=COLORS, line=dict(color="white", width=2)),
        textinfo="percent",
        hovertemplate=f"<b>%{{label}}</b><br>{value_label}: %{{value:,.0f}}<br>Share: %{{percent}}<extra></extra>",
    ))
    return _style(fig, title, height=height)


def treemap(df: pd.DataFrame, path: list[str], values: str, title: str, height: int = 460) -> go.Figure:
    if df.empty or df[values].sum() <= 0:
        return empty_figure()
    fig = px.treemap(df, path=path, values=values, color_discrete_sequence=COLORS)
    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>Purchase amount: $%{value:,.0f}<br>"
                      "Share of parent: %{percentParent:.1%}<br>Share of total: %{percentRoot:.1%}<extra></extra>",
        texttemplate="%{label}<br>$%{value:,.0f}", marker=dict(cornerradius=4))
    return _style(fig, title, height=height, legend=False)


def histogram(df: pd.DataFrame, x: str, title: str, x_label: str, nbins: int = 20,
              height: int = 340, prefix: str = "") -> go.Figure:
    if df.empty:
        return empty_figure()
    fig = px.histogram(df, x=x, nbins=nbins, opacity=0.75, color_discrete_sequence=COLORS)
    fig.update_traces(hovertemplate=f"{x_label}: {prefix}%{{x}}<br>Records: %{{y}}<extra></extra>")
    fig.update_xaxes(title=x_label, tickprefix=prefix, showgrid=False)
    fig.update_yaxes(title="Records", showgrid=True, gridcolor=GRID_COLOR)
    return _style(fig, title, height=height, legend=False)


def box(df: pd.DataFrame, x: str, y: str, title: str, x_label: str, y_label: str,
        prefix: str = "", height: int = 380) -> go.Figure:
    if df.empty:
        return empty_figure()
    fig = px.box(df, x=x, y=y, color=x, color_discrete_sequence=COLORS, points=False)
    fig.update_xaxes(title=x_label, showgrid=False)
    fig.update_yaxes(title=y_label, tickprefix=prefix, showgrid=True, gridcolor=GRID_COLOR)
    return _style(fig, title, height=height, legend=False)


def heatmap(pivot: pd.DataFrame, title: str, value_label: str, fmt: str = ",.0f", prefix: str = "",
            x_label: str = "", y_label: str = "", height: int = 400) -> go.Figure:
    if pivot.empty:
        return empty_figure()
    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=[str(c) for c in pivot.columns], y=[str(i) for i in pivot.index],
        colorscale="Blues", colorbar=dict(title=value_label, tickprefix=prefix),
        text=pivot.values, texttemplate=f"{prefix}%{{text:{fmt}}}",
        hovertemplate=f"<b>%{{y}}</b> x <b>%{{x}}</b><br>{value_label}: {prefix}%{{z:{fmt}}}<extra></extra>",
        hoverongaps=False,
    ))
    fig.update_xaxes(title=x_label, showgrid=False)
    fig.update_yaxes(title=y_label, showgrid=False, autorange="reversed")
    return _style(fig, title, height=height, legend=False)


def popularity_scatter(df: pd.DataFrame, title: str, height: int = 460) -> go.Figure:
    """Product popularity (records) vs average rating; bubble size = total amount."""
    rated = df.dropna(subset=["avg_rating"])
    if rated.empty:
        return empty_figure()
    fig = px.scatter(rated, x="records", y="avg_rating", size="total_amount", color="category",
                     hover_name="item_purchased", color_discrete_sequence=COLORS, size_max=38,
                     custom_data=["category", "total_amount"])
    fig.update_traces(hovertemplate="<b>%{hovertext}</b><br>Category: %{customdata[0]}<br>"
                                    "Records: %{x:,}<br>Avg rating: %{y:.2f}<br>"
                                    "Total amount: $%{customdata[1]:,.0f}<extra></extra>")
    fig.update_xaxes(title="Purchase records (popularity)", showgrid=True, gridcolor=GRID_COLOR)
    low, high = rated["avg_rating"].min(), rated["avg_rating"].max()
    padding = max(0.05, (high - low) * 0.2)
    fig.update_yaxes(title="Average review rating (out of 5)", range=[low - padding, high + padding],
                     showgrid=True, gridcolor=GRID_COLOR)
    return _style(fig, title, height=height)
