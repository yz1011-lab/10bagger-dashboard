"""Reusable Plotly chart builders for the 10-Bagger dashboard."""

from __future__ import annotations
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from utils.constants import PH_ELIMINATION, PH_HIGH_PROBABILITY, PH_INITIAL


def probability_gauge(ticker: str, current_ph: float) -> go.Figure:
    """Single-stock probability gauge chart."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=current_ph * 100,
        number={"suffix": "%", "font": {"size": 36}},
        title={"text": ticker, "font": {"size": 18}},
        gauge={
            "axis": {"range": [0, 100], "ticksuffix": "%"},
            "bar": {"color": "#FF6B35"},
            "steps": [
                {"range": [0, PH_ELIMINATION * 100], "color": "#3b1010"},
                {"range": [PH_ELIMINATION * 100, PH_INITIAL * 100], "color": "#2a1a10"},
                {"range": [PH_INITIAL * 100, PH_HIGH_PROBABILITY * 100], "color": "#1a2a1a"},
                {"range": [PH_HIGH_PROBABILITY * 100, 100], "color": "#0a3a0a"},
            ],
            "threshold": {
                "line": {"color": "white", "width": 2},
                "thickness": 0.8,
                "value": current_ph * 100,
            },
        },
    ))
    fig.update_layout(
        height=220,
        margin=dict(l=20, r=20, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#FAFAFA",
    )
    return fig


def probability_history_line(df: pd.DataFrame, ticker: str | None = None) -> go.Figure:
    """Line chart of P(H) over time for one or all stocks."""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="尚無更新記錄", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False, font=dict(size=16, color="gray"))
        fig.update_layout(height=350, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        return fig

    fig = px.line(
        df, x="created_at", y="new_ph", color="stock_ticker",
        title=f"{'P(H) 歷史走勢 — ' + ticker if ticker else '全股票 P(H) 走勢'}",
        labels={"created_at": "時間", "new_ph": "P(H)", "stock_ticker": "股票"},
    )
    # Threshold lines
    fig.add_hline(y=PH_HIGH_PROBABILITY, line_dash="dash", line_color="#22c55e",
                  annotation_text="高機率 50%", annotation_position="top left")
    fig.add_hline(y=PH_ELIMINATION, line_dash="dash", line_color="#ef4444",
                  annotation_text="淘汰線 5%", annotation_position="bottom left")
    fig.add_hline(y=PH_INITIAL, line_dash="dot", line_color="#888",
                  annotation_text="初始 15%", annotation_position="top left")
    fig.update_layout(
        height=400,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#FAFAFA",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(gridcolor="#333")
    fig.update_yaxes(gridcolor="#333", range=[0, 1])
    return fig


def track_confidence_bar(tracks: list[dict]) -> go.Figure:
    """Horizontal bar chart of track confidence levels."""
    if not tracks:
        fig = go.Figure()
        fig.add_annotation(text="尚無賽道資料", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False, font=dict(size=16, color="gray"))
        fig.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        return fig

    df = pd.DataFrame(tracks)
    colors = df["consensus_level"].map({
        "high": "#22c55e", "moderate": "#eab308", "contrarian": "#ef4444",
    }).fillna("#888")

    fig = go.Figure(go.Bar(
        x=df["confidence"],
        y=df["name"],
        orientation="h",
        marker_color=colors,
        text=df["confidence"].apply(lambda v: f"{v:.0f}%"),
        textposition="auto",
    ))
    fig.update_layout(
        title="賽道信心指數",
        height=max(200, len(tracks) * 45 + 80),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#FAFAFA",
        xaxis=dict(range=[0, 100], title="Confidence", gridcolor="#333"),
        yaxis=dict(autorange="reversed"),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def evidence_timeline(df: pd.DataFrame) -> go.Figure:
    """Scatter plot of evidence entries over time."""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="尚無證據記錄", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False, font=dict(size=16, color="gray"))
        fig.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        return fig

    fig = px.scatter(
        df, x="created_at", y="stock_ticker",
        title="證據記錄時間軸",
        labels={"created_at": "時間", "stock_ticker": "股票"},
    )
    fig.update_traces(marker=dict(size=10, color="#FF6B35"))
    fig.update_layout(
        height=300,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#FAFAFA",
    )
    return fig
