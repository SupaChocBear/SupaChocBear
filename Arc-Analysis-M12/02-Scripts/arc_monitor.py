"""
arc_monitor.py
==============
Streamlit web dashboard for Arc Analysis M12.

What this script does:
  1. Lets you upload the sensor CSV file directly in the browser.
  2. Parses the flexible CSV format automatically (handles non-standard headers).
  3. Detects arc events using a statistical threshold (mean + 3 standard deviations).
  4. Shows interactive time-series charts for Arc intensity, Height, and Distance.
  5. Draws a GPS track map coloured by arc intensity.
  6. Lets you download a cleaned CSV and an events-only CSV.

Run with:
    streamlit run 02-Scripts/arc_monitor.py

Then open the URL shown in the terminal (usually http://localhost:8501).
"""

import io
import os

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# PAGE CONFIG — sets browser tab title and layout
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Arc Monitor — M12",
    page_icon="⚡",
    layout="wide",
)

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

# Statistical threshold multiplier for arc event detection.
# "mean + 3 × standard deviation" captures the top ~0.3% of readings.
SIGMA_MULTIPLIER = 3

# Expected column name patterns (lowercase).  The parser will try to match
# column headers from the CSV against these keywords.
COL_KEYWORDS = {
    "arc": ["arc", "µa", "ua", "microamp"],
    "distance": ["distance", "dist", "metres", "meter", "chainage"],
    "height": ["height", "elevation", "asl", "altitude"],
    "latitude": ["lat", "latitude"],
    "longitude": ["lon", "lng", "longitude"],
}

# ---------------------------------------------------------------------------
# PARSING HELPERS
# ---------------------------------------------------------------------------


def find_column(df: pd.DataFrame, keywords: list[str]) -> str | None:
    """
    Search the DataFrame columns for one that contains any of the
    provided keywords (case-insensitive).  Returns the first match or None.

    Why do this?  Railway sensor CSVs often have column names like
    'Arc (µA/cm²) 14:32:01' — we need to find 'Arc' even with extras.
    """
    for col in df.columns:
        col_lower = col.lower()
        if any(kw in col_lower for kw in keywords):
            return col
    return None


def parse_flexible_csv(uploaded_file) -> pd.DataFrame | None:
    """
    Parse the uploaded CSV file with a flexible strategy:

    1. Try reading normally.
    2. If column detection fails, try skipping the first 1–3 rows
       (some files have a title or units row before the real header).
    3. Map found columns to standardised names:
       arc, distance, height, latitude, longitude.

    Returns a clean DataFrame with standardised column names,
    or None if parsing fails.
    """
    content = uploaded_file.read()
    uploaded_file.seek(0)  # rewind so Streamlit can re-read if needed

    best_df = None
    best_score = 0

    # Try different header row positions
    for skip_rows in [0, 1, 2, 3]:
        try:
            df = pd.read_csv(
                io.BytesIO(content),
                skiprows=skip_rows,
                low_memory=False,
                encoding_errors="replace",
            )
        except Exception:
            continue

        # Score this attempt: count how many expected columns we can find
        score = sum(
            1 for kws in COL_KEYWORDS.values() if find_column(df, kws) is not None
        )
        if score > best_score:
            best_score = score
            best_df = df

    if best_df is None or best_score == 0:
        return None

    # Build a clean DataFrame with standardised column names
    clean = {}
    for std_name, keywords in COL_KEYWORDS.items():
        raw_col = find_column(best_df, keywords)
        if raw_col is not None:
            # Convert to numeric, coercing any text/unit strings to NaN
            clean[std_name] = pd.to_numeric(best_df[raw_col], errors="coerce")

    return pd.DataFrame(clean)


# ---------------------------------------------------------------------------
# ARC EVENT DETECTION
# ---------------------------------------------------------------------------


def detect_events(df: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """
    Mark rows where arc intensity exceeds the threshold as events.
    Adds a boolean column 'is_event' to the DataFrame.
    """
    df = df.copy()
    df["is_event"] = df["arc"] > threshold
    return df


# ---------------------------------------------------------------------------
# CHART BUILDERS
# ---------------------------------------------------------------------------


def chart_arc_timeseries(df: pd.DataFrame, threshold: float) -> go.Figure:
    """
    Line chart of arc intensity over distance.
    A horizontal dashed red line marks the event detection threshold.
    Event points are highlighted in red.
    """
    fig = go.Figure()

    # Main arc intensity line
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["arc"],
        mode="lines",
        name="Arc (µA/cm²)",
        line=dict(color="#1f77b4", width=1),
    ))

    # Highlight event points in red
    events = df[df["is_event"]]
    if not events.empty:
        fig.add_trace(go.Scatter(
            x=events.index,
            y=events["arc"],
            mode="markers",
            name="Arc Event",
            marker=dict(color="red", size=6, symbol="circle"),
        ))

    # Threshold line
    fig.add_hline(
        y=threshold,
        line_dash="dash",
        line_color="red",
        annotation_text=f"Threshold ({threshold:.2f} µA/cm²)",
        annotation_position="top right",
    )

    fig.update_layout(
        title="Arc Intensity Along Track",
        xaxis_title="Sample index",
        yaxis_title="Arc (µA/cm²)",
        hovermode="x unified",
        height=400,
    )
    return fig


def chart_height(df: pd.DataFrame) -> go.Figure:
    """
    Line chart of track height above sea level.
    """
    fig = px.line(
        df,
        y="height",
        title="Track Height (m ASL)",
        labels={"index": "Sample index", "height": "Height (m ASL)"},
    )
    fig.update_layout(height=350)
    return fig


def chart_distance(df: pd.DataFrame) -> go.Figure:
    """
    Line chart of cumulative distance along the track.
    """
    fig = px.line(
        df,
        y="distance",
        title="Distance Along Track (m)",
        labels={"index": "Sample index", "distance": "Distance (m)"},
    )
    fig.update_layout(height=350)
    return fig


def chart_gps_map(df: pd.DataFrame) -> go.Figure | None:
    """
    Scatter map of the GPS track, coloured by arc intensity.
    Red = high arc, blue = low arc.

    Returns None if latitude/longitude columns are not present.
    """
    if "latitude" not in df.columns or "longitude" not in df.columns:
        return None
    if df["latitude"].isna().all() or df["longitude"].isna().all():
        return None

    fig = px.scatter_mapbox(
        df.dropna(subset=["latitude", "longitude"]),
        lat="latitude",
        lon="longitude",
        color="arc",
        color_continuous_scale="RdYlGn_r",  # red = high arc
        size_max=8,
        zoom=14,
        mapbox_style="open-street-map",
        title="GPS Track — Coloured by Arc Intensity",
        hover_data={
            "arc": ":.3f",
            "distance": ":.1f",
            "height": ":.1f",
        },
        labels={"arc": "Arc (µA/cm²)"},
    )
    fig.update_layout(height=500)
    return fig


# ---------------------------------------------------------------------------
# CSV DOWNLOAD HELPERS
# ---------------------------------------------------------------------------


def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Convert a DataFrame to UTF-8 CSV bytes for download."""
    return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")


# ---------------------------------------------------------------------------
# MAIN STREAMLIT APP
# ---------------------------------------------------------------------------


def main():
    # ── Header ──────────────────────────────────────────────────────────────
    st.title("⚡ Arc Monitor — Mileage Marker M12")
    st.markdown(
        "Upload your sensor CSV file to inspect arc events, "
        "visualise the track, and export results."
    )

    # ── File Upload ──────────────────────────────────────────────────────────
    uploaded = st.file_uploader(
        "Upload sensor CSV file",
        type=["csv", "txt"],
        help="The raw CSV from 01-Raw-Data. Original file is never modified.",
    )

    if uploaded is None:
        st.info("Please upload a CSV file to begin.")
        return

    # ── Parse CSV ────────────────────────────────────────────────────────────
    with st.spinner("Parsing CSV …"):
        df = parse_flexible_csv(uploaded)

    if df is None or df.empty:
        st.error(
            "Could not parse the CSV file.  "
            "Please check that it contains Arc, Distance, Height, "
            "Latitude, and Longitude columns."
        )
        return

    st.success(f"Loaded {len(df):,} rows.")

    # ── Sidebar Controls ────────────────────────────────────────────────────
    st.sidebar.header("Detection Settings")

    if "arc" in df.columns and df["arc"].notna().any():
        arc_mean = df["arc"].mean()
        arc_std = df["arc"].std()
        default_threshold = arc_mean + SIGMA_MULTIPLIER * arc_std

        threshold = st.sidebar.number_input(
            label="Arc event threshold (µA/cm²)",
            value=float(round(default_threshold, 4)),
            step=0.0001,
            format="%.4f",
            help=f"Default = mean + {SIGMA_MULTIPLIER}σ = {default_threshold:.4f}",
        )

        st.sidebar.markdown(
            f"**Dataset stats:**  \n"
            f"Mean: `{arc_mean:.4f}` µA/cm²  \n"
            f"Std dev: `{arc_std:.4f}` µA/cm²  \n"
            f"Threshold: `{threshold:.4f}` µA/cm²"
        )
    else:
        st.error("Arc column not found or is empty.  Cannot detect events.")
        return

    # ── Detect Events ────────────────────────────────────────────────────────
    df = detect_events(df, threshold)
    events_df = df[df["is_event"]].copy()
    n_events = len(events_df)

    # ── Summary Metrics ──────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total samples", f"{len(df):,}")
    col2.metric("Arc events detected", f"{n_events:,}")
    col3.metric("Max arc (µA/cm²)", f"{df['arc'].max():.4f}")
    col4.metric("Mean arc (µA/cm²)", f"{df['arc'].mean():.4f}")

    st.divider()

    # ── Arc Intensity Chart ──────────────────────────────────────────────────
    st.plotly_chart(chart_arc_timeseries(df, threshold), use_container_width=True)

    # ── Height & Distance Charts ─────────────────────────────────────────────
    if "height" in df.columns and df["height"].notna().any():
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(chart_height(df), use_container_width=True)
        if "distance" in df.columns and df["distance"].notna().any():
            with c2:
                st.plotly_chart(chart_distance(df), use_container_width=True)
    elif "distance" in df.columns and df["distance"].notna().any():
        st.plotly_chart(chart_distance(df), use_container_width=True)

    # ── GPS Map ──────────────────────────────────────────────────────────────
    map_fig = chart_gps_map(df)
    if map_fig is not None:
        st.divider()
        st.plotly_chart(map_fig, use_container_width=True)
    else:
        st.info("GPS map not shown — latitude/longitude data not found.")

    # ── Events Table ─────────────────────────────────────────────────────────
    st.divider()
    st.subheader(f"Detected Arc Events ({n_events:,})")
    if n_events > 0:
        st.dataframe(
            events_df.drop(columns=["is_event"], errors="ignore"),
            use_container_width=True,
            height=300,
        )
    else:
        st.success("No arc events detected above the current threshold.")

    # ── Downloads ────────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Export")

    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button(
            label="Download cleaned CSV",
            data=df_to_csv_bytes(df.drop(columns=["is_event"], errors="ignore")),
            file_name="arc_m12_cleaned.csv",
            mime="text/csv",
        )
    with dl2:
        if n_events > 0:
            st.download_button(
                label="Download events CSV",
                data=df_to_csv_bytes(events_df.drop(columns=["is_event"], errors="ignore")),
                file_name="arc_m12_events.csv",
                mime="text/csv",
            )
        else:
            st.button("Download events CSV", disabled=True)


if __name__ == "__main__":
    main()
