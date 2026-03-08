"""
electrical_dashboard.py
=======================
Dynamic Plotly / Dash dashboard for electrical measurements data.

Prerequisites
-------------
  Run electrical_data_loader.py first to generate data/electrical_data.parquet.

Run with:
    python scripts/electrical_dashboard.py

Then open: http://127.0.0.1:8050

Dashboard layout
----------------
  ┌─────────────────────────────────────────────────────┐
  │  KPI row: total samples | date range | voltage stats│
  │           | current stats                           │
  ├─────────────────────────────────────────────────────┤
  │  Controls: date-range picker  |  refresh interval   │
  │            column selector    |  aggregation window │
  ├─────────────────────────────────────────────────────┤
  │  Tab 1 — Voltages                                   │
  │    Multi-line chart: AN(V) BN(V) CN(V) NG(V)        │
  │    Phase-balance bar chart                          │
  ├─────────────────────────────────────────────────────┤
  │  Tab 2 — Currents                                   │
  │    Multi-line chart: A(A) B(A) C(A) N(A)            │
  │    Current-balance bar chart                        │
  ├─────────────────────────────────────────────────────┤
  │  Tab 3 — Statistics table                           │
  │    min / mean / max / std / null% per column        │
  └─────────────────────────────────────────────────────┘
"""

import os
import sys

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dcc, html, dash_table
import dash_bootstrap_components as dbc

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

DATA_FILE = os.path.join(_PROJECT_ROOT, "data", "electrical_data.parquet")

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

VOLTAGE_COLS = ["AN(V)", "BN(V)", "CN(V)", "NG(V)"]
CURRENT_COLS = ["A(A)", "B(A)", "C(A)", "N(A)"]

VOLTAGE_COLORS = ["#636EFA", "#EF553B", "#00CC96", "#AB63FA"]
CURRENT_COLORS = ["#FFA15A", "#19D3F3", "#FF6692", "#B6E880"]

REFRESH_OPTIONS = [
    {"label": "Off",      "value": 0},
    {"label": "10 s",     "value": 10_000},
    {"label": "30 s",     "value": 30_000},
    {"label": "1 min",    "value": 60_000},
    {"label": "5 min",    "value": 300_000},
]

ROLLING_OPTIONS = [
    {"label": "None",     "value": 1},
    {"label": "10 pts",   "value": 10},
    {"label": "50 pts",   "value": 50},
    {"label": "100 pts",  "value": 100},
    {"label": "500 pts",  "value": 500},
]

# ---------------------------------------------------------------------------
# DATA LOADING
# ---------------------------------------------------------------------------


def load_parquet() -> pd.DataFrame:
    """Load the pre-processed parquet written by electrical_data_loader.py."""
    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError(
            f"Data file not found: {DATA_FILE}\n"
            "Run  python scripts/electrical_data_loader.py  first."
        )
    df = pd.read_parquet(DATA_FILE, engine="pyarrow")
    if "DateTime" in df.columns:
        df = df.sort_values("DateTime").reset_index(drop=True)
    return df


# Load once at startup; the refresh callback re-reads from disk on demand.
try:
    _df_cache: pd.DataFrame = load_parquet()
    _load_error: str | None = None
except Exception as exc:
    _df_cache = pd.DataFrame()
    _load_error = str(exc)

# ---------------------------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------------------------


def _present_cols(df: pd.DataFrame, wanted: list[str]) -> list[str]:
    """Return only the columns from 'wanted' that actually exist in df."""
    return [c for c in wanted if c in df.columns]


def _apply_rolling(df: pd.DataFrame, cols: list[str], window: int) -> pd.DataFrame:
    if window > 1:
        df = df.copy()
        df[cols] = df[cols].rolling(window, min_periods=1, center=True).mean()
    return df


def _filter_by_date(
    df: pd.DataFrame, start: str | None, end: str | None
) -> pd.DataFrame:
    if "DateTime" not in df.columns or df.empty:
        return df
    mask = pd.Series([True] * len(df), index=df.index)
    if start:
        mask &= df["DateTime"] >= pd.Timestamp(start)
    if end:
        mask &= df["DateTime"] <= pd.Timestamp(end) + pd.Timedelta(days=1)
    return df[mask].reset_index(drop=True)


def _kpi_value(df: pd.DataFrame, col: str, stat: str) -> str:
    if col not in df.columns or df[col].dropna().empty:
        return "—"
    s = df[col].dropna()
    if stat == "mean":
        return f"{s.mean():.2f}"
    if stat == "max":
        return f"{s.max():.2f}"
    if stat == "min":
        return f"{s.min():.2f}"
    return "—"


# ---------------------------------------------------------------------------
# CHART BUILDERS
# ---------------------------------------------------------------------------


def build_timeseries(
    df: pd.DataFrame,
    cols: list[str],
    colors: list[str],
    title: str,
    y_label: str,
) -> go.Figure:
    """Multi-line time-series chart."""
    x_axis = df["DateTime"] if "DateTime" in df.columns else df.index

    fig = go.Figure()
    for col, color in zip(cols, colors):
        if col not in df.columns:
            continue
        fig.add_trace(
            go.Scatter(
                x=x_axis,
                y=df[col],
                mode="lines",
                name=col,
                line=dict(color=color, width=1.5),
                hovertemplate=f"<b>{col}</b><br>%{{x}}<br>%{{y:.3f}}<extra></extra>",
            )
        )

    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        xaxis_title="DateTime" if "DateTime" in df.columns else "Sample index",
        yaxis_title=y_label,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=420,
        margin=dict(l=60, r=20, t=60, b=50),
        template="plotly_dark",
    )
    return fig


def build_balance_bar(
    df: pd.DataFrame, cols: list[str], colors: list[str], title: str, y_label: str
) -> go.Figure:
    """Bar chart showing mean ± std for each channel (phase balance view)."""
    means = [df[c].mean() if c in df.columns else None for c in cols]
    stds  = [df[c].std()  if c in df.columns else None for c in cols]

    fig = go.Figure(
        go.Bar(
            x=cols,
            y=means,
            error_y=dict(type="data", array=stds, visible=True),
            marker_color=colors,
            text=[f"{m:.2f}" if m is not None else "N/A" for m in means],
            textposition="outside",
        )
    )
    fig.update_layout(
        title=dict(text=title, font=dict(size=14)),
        yaxis_title=y_label,
        height=300,
        margin=dict(l=60, r=20, t=50, b=40),
        template="plotly_dark",
        showlegend=False,
    )
    return fig


def build_stats_table(df: pd.DataFrame, cols: list[str]) -> list[dict]:
    """Build rows for the Dash DataTable stats view."""
    rows = []
    for col in cols:
        if col not in df.columns:
            continue
        s = df[col]
        null_pct = f"{s.isna().mean() * 100:.1f}%"
        s_clean  = s.dropna()
        rows.append({
            "Column":    col,
            "Count":     f"{len(s_clean):,}",
            "Null %":    null_pct,
            "Min":       f"{s_clean.min():.4f}"  if not s_clean.empty else "—",
            "Mean":      f"{s_clean.mean():.4f}" if not s_clean.empty else "—",
            "Max":       f"{s_clean.max():.4f}"  if not s_clean.empty else "—",
            "Std dev":   f"{s_clean.std():.4f}"  if not s_clean.empty else "—",
        })
    return rows


# ---------------------------------------------------------------------------
# APP LAYOUT
# ---------------------------------------------------------------------------


def _make_kpi_card(label: str, value: str, color: str = "#636EFA") -> dbc.Card:
    return dbc.Card(
        dbc.CardBody([
            html.P(label, className="mb-0", style={"fontSize": "0.75rem", "color": "#aaa"}),
            html.H5(value, style={"color": color, "fontWeight": "bold", "margin": 0}),
        ]),
        style={"background": "#1e1e2e", "border": f"1px solid {color}33"},
        className="text-center p-2",
    )


def build_layout(df: pd.DataFrame) -> html.Div:
    v_cols = _present_cols(df, VOLTAGE_COLS)
    i_cols = _present_cols(df, CURRENT_COLS)

    # Date-picker bounds
    dt_min = dt_max = None
    if "DateTime" in df.columns and not df.empty:
        dt_min = df["DateTime"].min().date().isoformat()
        dt_max = df["DateTime"].max().date().isoformat()

    # KPI cards
    n_rows    = f"{len(df):,}" if not df.empty else "—"
    date_span = (
        f"{dt_min} → {dt_max}" if dt_min and dt_max else "—"
    )
    v_mean_an = _kpi_value(df, "AN(V)", "mean")
    v_max_cn  = _kpi_value(df, "CN(V)", "max")
    i_mean_a  = _kpi_value(df, "A(A)",  "mean")
    i_max_a   = _kpi_value(df, "A(A)",  "max")

    kpi_row = dbc.Row(
        [
            dbc.Col(_make_kpi_card("Total samples", n_rows),             width=2),
            dbc.Col(_make_kpi_card("Date range",    date_span, "#aaa"),  width=3),
            dbc.Col(_make_kpi_card("AN(V) mean",    v_mean_an, "#636EFA"), width=2),
            dbc.Col(_make_kpi_card("CN(V) max",     v_max_cn,  "#EF553B"), width=2),
            dbc.Col(_make_kpi_card("A(A) mean",     i_mean_a,  "#FFA15A"), width=2),
            dbc.Col(_make_kpi_card("A(A) peak",     i_max_a,   "#FF6692"), width=1),
        ],
        className="g-2 mb-3",
    )

    # Controls
    controls = dbc.Card(
        dbc.CardBody(
            dbc.Row([
                dbc.Col([
                    html.Label("Date range", className="fw-bold text-light mb-1"),
                    dcc.DatePickerRange(
                        id="date-picker",
                        min_date_allowed=dt_min,
                        max_date_allowed=dt_max,
                        start_date=dt_min,
                        end_date=dt_max,
                        display_format="DD/MM/YYYY",
                        style={"width": "100%"},
                    ),
                ], width=4),
                dbc.Col([
                    html.Label("Rolling average", className="fw-bold text-light mb-1"),
                    dcc.Dropdown(
                        id="rolling-window",
                        options=ROLLING_OPTIONS,
                        value=1,
                        clearable=False,
                        style={"color": "#000"},
                    ),
                ], width=3),
                dbc.Col([
                    html.Label("Auto-refresh", className="fw-bold text-light mb-1"),
                    dcc.Dropdown(
                        id="refresh-interval-select",
                        options=REFRESH_OPTIONS,
                        value=0,
                        clearable=False,
                        style={"color": "#000"},
                    ),
                ], width=3),
                dbc.Col([
                    html.Label("\u00a0", className="d-block mb-1"),
                    dbc.Button(
                        "Refresh now",
                        id="refresh-btn",
                        color="primary",
                        className="w-100",
                    ),
                ], width=2),
            ])
        ),
        style={"background": "#1e1e2e", "border": "1px solid #333"},
        className="mb-3",
    )

    # Tabs
    tabs = dbc.Tabs(
        [
            dbc.Tab(
                label="Voltages",
                tab_id="tab-voltage",
                children=[
                    dcc.Graph(id="graph-voltage-ts"),
                    dcc.Graph(id="graph-voltage-bar"),
                ],
            ),
            dbc.Tab(
                label="Currents",
                tab_id="tab-current",
                children=[
                    dcc.Graph(id="graph-current-ts"),
                    dcc.Graph(id="graph-current-bar"),
                ],
            ),
            dbc.Tab(
                label="Statistics",
                tab_id="tab-stats",
                children=[
                    html.Div(id="stats-table", className="p-3"),
                ],
            ),
        ],
        id="main-tabs",
        active_tab="tab-voltage",
        className="mb-3",
    )

    # Interval component (driven by dropdown)
    interval = dcc.Interval(id="auto-refresh", interval=0, disabled=True)

    return html.Div(
        [
            dbc.NavbarSimple(
                brand="Electrical Measurements Dashboard",
                brand_href="#",
                color="dark",
                dark=True,
                className="mb-3",
            ),
            dbc.Container(
                [kpi_row, controls, tabs, interval],
                fluid=True,
            ),
        ],
        style={"background": "#13131f", "minHeight": "100vh"},
    )


# ---------------------------------------------------------------------------
# APP INITIALISATION
# ---------------------------------------------------------------------------

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    title="Electrical Dashboard",
    suppress_callback_exceptions=True,
)

app.layout = build_layout(_df_cache)

# ---------------------------------------------------------------------------
# CALLBACKS
# ---------------------------------------------------------------------------


@app.callback(
    Output("auto-refresh", "interval"),
    Output("auto-refresh", "disabled"),
    Input("refresh-interval-select", "value"),
)
def set_refresh_interval(value: int):
    if not value:
        return 60_000, True        # disabled — interval value doesn't matter
    return value, False


@app.callback(
    Output("graph-voltage-ts",  "figure"),
    Output("graph-voltage-bar", "figure"),
    Output("graph-current-ts",  "figure"),
    Output("graph-current-bar", "figure"),
    Output("stats-table",       "children"),
    Input("refresh-btn",         "n_clicks"),
    Input("auto-refresh",        "n_intervals"),
    State("date-picker",         "start_date"),
    State("date-picker",         "end_date"),
    State("rolling-window",      "value"),
)
def update_all(
    _n_clicks,
    _n_intervals,
    start_date: str | None,
    end_date:   str | None,
    rolling:    int,
):
    """
    Master callback — re-reads the parquet file, applies date filter and
    rolling average, then rebuilds all four charts and the stats table.
    """
    # Re-read from disk so new loader runs are picked up automatically
    try:
        df = load_parquet()
    except Exception as exc:
        empty_fig = go.Figure().update_layout(
            template="plotly_dark",
            title=str(exc),
        )
        return empty_fig, empty_fig, empty_fig, empty_fig, html.P(str(exc))

    df = _filter_by_date(df, start_date, end_date)

    v_cols = _present_cols(df, VOLTAGE_COLS)
    i_cols = _present_cols(df, CURRENT_COLS)

    df_v = _apply_rolling(df, v_cols, rolling) if v_cols else df
    df_i = _apply_rolling(df, i_cols, rolling) if i_cols else df

    # ── Voltage time-series ───────────────────────────────────────────────
    v_ts = build_timeseries(
        df_v, v_cols, VOLTAGE_COLORS[:len(v_cols)],
        title="Phase-to-Neutral Voltages over Time",
        y_label="Voltage (V)",
    )

    # ── Voltage balance bar ───────────────────────────────────────────────
    v_bar = build_balance_bar(
        df, v_cols, VOLTAGE_COLORS[:len(v_cols)],
        title="Voltage Phase Balance  (mean ± 1σ)",
        y_label="Voltage (V)",
    )

    # ── Current time-series ───────────────────────────────────────────────
    i_ts = build_timeseries(
        df_i, i_cols, CURRENT_COLORS[:len(i_cols)],
        title="Line Currents over Time",
        y_label="Current (A)",
    )

    # ── Current balance bar ───────────────────────────────────────────────
    i_bar = build_balance_bar(
        df, i_cols, CURRENT_COLORS[:len(i_cols)],
        title="Current Phase Balance  (mean ± 1σ)",
        y_label="Current (A)",
    )

    # ── Statistics table ──────────────────────────────────────────────────
    rows = build_stats_table(df, v_cols + i_cols)
    table = dash_table.DataTable(
        data=rows,
        columns=[{"name": c, "id": c} for c in rows[0].keys()] if rows else [],
        style_table={"overflowX": "auto"},
        style_cell={
            "textAlign": "right",
            "padding": "6px 12px",
            "background": "#1e1e2e",
            "color": "#e0e0e0",
            "border": "1px solid #333",
            "fontFamily": "monospace",
        },
        style_header={
            "background": "#2a2a3e",
            "color": "#ffffff",
            "fontWeight": "bold",
            "border": "1px solid #444",
        },
        style_data_conditional=[
            {
                "if": {"row_index": "odd"},
                "backgroundColor": "#16162a",
            }
        ],
        page_size=20,
    ) if rows else html.P("No data available.", className="text-muted")

    return v_ts, v_bar, i_ts, i_bar, table


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if _load_error:
        print(f"\n[ERROR] {_load_error}")
        print("Run:  python scripts/electrical_data_loader.py\n")
        sys.exit(1)

    print()
    print("=" * 60)
    print("  Electrical Measurements Dashboard")
    print(f"  Loaded {len(_df_cache):,} rows from {DATA_FILE}")
    print("  Open: http://127.0.0.1:8050")
    print("=" * 60)
    print()

    app.run(debug=False, host="127.0.0.1", port=8050)
