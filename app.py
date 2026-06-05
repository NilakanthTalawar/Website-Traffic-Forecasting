import os
import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data_generator import (
    generate_traffic_data, generate_hourly_data,
    generate_country_data, parse_ga4_upload
)
from forecaster import run_forecast

# Website name input
website_name = "WebPulse"  # default
# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TrafficLens · Forecasting Dashboard",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Purple Dark Theme CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --bg-base:    #07071a;
    --bg-card:    #10102a;
    --bg-card2:   #16163a;
    --purple-1:   #7c3aed;
    --purple-2:   #a855f7;
    --purple-3:   #c084fc;
    --cyan:       #22d3ee;
    --green:      #34d399;
    --red:        #f87171;
    --text-main:  #f1f0ff;
    --text-muted: #8b8aad;
    --border:     rgba(124,58,237,0.25);
}

html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
    background-color: var(--bg-base) !important;
    color: var(--text-main) !important;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.5rem 2rem 3rem 2rem !important; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: var(--bg-card) !important;
    border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] * { color: var(--text-main) !important; }

/* Metric cards */
[data-testid="metric-container"] {
    background: var(--bg-card2);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1rem 1.25rem;
    box-shadow: 0 0 24px rgba(124,58,237,0.08);
}
[data-testid="metric-container"] label {
    color: var(--text-muted) !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: var(--purple-3) !important;
    font-size: 1.9rem !important;
    font-weight: 800 !important;
}
[data-testid="metric-container"] [data-testid="stMetricDelta"] {
    font-size: 0.8rem !important;
}

/* Divider */
hr { border-color: var(--border) !important; }

/* Tabs */
[data-baseweb="tab-list"] {
    background: var(--bg-card) !important;
    border-radius: 10px;
    gap: 4px;
    padding: 4px;
}
[data-baseweb="tab"] {
    border-radius: 8px !important;
    color: var(--text-muted) !important;
    font-weight: 600 !important;
    letter-spacing: 0.03em;
}
[aria-selected="true"] {
    background: var(--purple-1) !important;
    color: white !important;
}

/* Dataframe */
[data-testid="stDataFrame"] { border: 1px solid var(--border); border-radius: 10px; }

/* File uploader */
[data-testid="stFileUploader"] {
    border: 2px dashed var(--purple-1) !important;
    border-radius: 14px !important;
    background: var(--bg-card) !important;
    padding: 1rem;
}

/* Section headers */
.section-header {
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--purple-3);
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin-bottom: 0.5rem;
    padding-left: 0.5rem;
    border-left: 3px solid var(--purple-1);
}

/* Custom title */
.dash-title {
    font-size: 2.4rem;
    font-weight: 800;
    background: linear-gradient(135deg, #c084fc 0%, #22d3ee 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.02em;
    line-height: 1.1;
}
.dash-sub {
    color: var(--text-muted);
    font-size: 0.9rem;
    margin-top: 0.25rem;
    font-family: 'JetBrains Mono', monospace;
}

/* Badge */
.badge {
    display: inline-block;
    background: rgba(124,58,237,0.2);
    border: 1px solid var(--purple-1);
    color: var(--purple-3);
    border-radius: 20px;
    padding: 2px 12px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}
</style>
""", unsafe_allow_html=True)

# ── Plotly dark template ───────────────────────────────────────────────────────
PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(16,16,42,0.6)",
    font=dict(family="Syne", color="#f1f0ff", size=12),
    xaxis=dict(gridcolor="rgba(124,58,237,0.12)", zerolinecolor="rgba(124,58,237,0.2)"),
    yaxis=dict(gridcolor="rgba(124,58,237,0.12)", zerolinecolor="rgba(124,58,237,0.2)"),
    legend=dict(bgcolor="rgba(16,16,42,0.8)", bordercolor="rgba(124,58,237,0.3)", borderwidth=1),
    margin=dict(l=40, r=20, t=40, b=40),
    hovermode="x unified",
)
PURPLE_SEQ = ["#3b0764","#6d28d9","#7c3aed","#a855f7","#c084fc","#e879f9","#22d3ee"]
SOURCE_COLORS = ["#7c3aed","#a855f7","#22d3ee","#34d399","#f59e0b","#f87171","#e879f9","#818cf8"]


# ── Helpers ────────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    os.makedirs("data", exist_ok=True)
    if os.path.exists("data/traffic.csv"):
        df = pd.read_csv("data/traffic.csv")
    else:
        df = generate_traffic_data()
    df["Date"] = pd.to_datetime(df["Date"], format="%Y%m%d", errors="coerce")
    df = df.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)
    return df

@st.cache_data
def get_hourly(df):
    return generate_hourly_data(df)

@st.cache_data
def get_countries(df):
    return generate_country_data(df)

def get_forecast_v2(df, periods):
    return run_forecast(df, periods=periods)

def apply_layout(fig, title=""):
    fig.update_layout(**PLOT_LAYOUT)
    if title:
        fig.update_layout(title=dict(text=title, font=dict(size=14, color="#c084fc"), x=0))
    return fig


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f'<div class="dash-title">📡 {website_name}</div>', unsafe_allow_html=True)
    st.markdown('<div class="dash-sub">Website Forecasting Suite</div>', unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("### 📁 Data Source")
    use_upload = st.toggle("Upload GA4 CSV", value=False)

    uploaded_file = None
    if use_upload:
        uploaded_file = st.file_uploader(
            "Drop GA4 export CSV",
            type=["csv"],
            help="Export from GA4: Reports → Export → CSV"
        )
        st.markdown('<span class="badge">GA4 Format</span>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### ⚙️ Forecast Settings")
    forecast_days = st.select_slider(
        "Forecast horizon",
        options=[30, 60, 90, 120, 180],
        value=90
    )
    st.markdown("### 🌐 Website")
    website_name = st.text_input("Website Name", value="My Website", placeholder="e.g. myshop.com")
    st.markdown("---")
    
    


# ── Load data ──────────────────────────────────────────────────────────────────
if uploaded_file is not None:
    try:
        df_raw = parse_ga4_upload(uploaded_file)
        df_raw["Date"] = pd.to_datetime(df_raw["Date"], format="%Y%m%d", errors="coerce")
        df_raw = df_raw.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)
        st.sidebar.success(f"✅ Loaded {len(df_raw):,} rows")
        df = df_raw
    except Exception as e:
        st.sidebar.error(f"Parse error: {e}")
        df = load_data()
else:
    df = load_data()

# Date range filter
with st.sidebar:
    date_min, date_max = df["Date"].min().date(), df["Date"].max().date()
    years = sorted(df["Date"].dt.year.unique().tolist())
    selected_year = st.selectbox("Select Year", ["All"] + [str(y) for y in years])

selected_year = selected_year if 'selected_year' in dir() else "All"

if selected_year == "All":
    df_f = df.copy()
else:
    df_f = df[df["Date"].dt.year == int(selected_year)].reset_index(drop=True)

if len(df_f) == 0:
    st.warning("No data for selected year.")
    st.stop()

    st.markdown("### 📅 Year Filter")
    years = sorted(df["Date"].dt.year.unique().tolist())
    years_options = ["All"] + [str(y) for y in years]
    selected_year = st.selectbox("Select Year", years_options)
# ── Title ──────────────────────────────────────────────────────────────────────
col_t, col_b = st.columns([3, 1])
with col_t:
    st.markdown('<div class="dash-title">Website Traffic Forecasting</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="dash-sub">Prophet · Isolation-free · {len(df_f):,} data points · {df_f["Date"].min().date()} → {df_f["Date"].max().date()}</div>', unsafe_allow_html=True)
with col_b:
    st.markdown('<br>', unsafe_allow_html=True)
    st.markdown('<span class="badge">ML · Time Series · DS Pipeline</span>', unsafe_allow_html=True)

st.markdown("---")

# ── KPI Cards ──────────────────────────────────────────────────────────────────
total_sessions = int(df_f["Sessions"].sum())
total_users = int(df_f["Users"].sum()) if "Users" in df_f.columns else int(total_sessions * 0.78)
total_conversions = int(df_f["Conversions"].sum()) if "Conversions" in df_f.columns else 0
avg_cvr = round(df_f["Conversion Rate"].mean(), 2) if "Conversion Rate" in df_f.columns else 0
top_source = df_f["Source / Medium"].mode()[0] if "Source / Medium" in df_f.columns else "organic"

# Delta vs prev period
half = len(df_f) // 2
prev_sessions = int(df_f.iloc[:half]["Sessions"].sum()) if half > 0 else total_sessions
curr_sessions = int(df_f.iloc[half:]["Sessions"].sum()) if half > 0 else total_sessions
delta_pct = round((curr_sessions - prev_sessions) / max(prev_sessions, 1) * 100, 1)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Sessions", f"{total_sessions:,}", f"{delta_pct:+.1f}% vs prev period")
k2.metric("Total Users", f"{total_users:,}")
k3.metric("Conversions", f"{total_conversions:,}")
k4.metric("Avg Conv. Rate", f"{avg_cvr:.2f}%")
k5.metric("Top Source", top_source.split(" / ")[0].title())

st.markdown("---")

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Traffic Overview",
    "🔮 Forecast",
    "🌍 Geography",
    "🕐 Peak Hours",
    "📊 Conversions"
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Traffic Overview
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown('<div class="section-header">Sessions & Users Over Time</div>', unsafe_allow_html=True)

    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=df_f["Date"], y=df_f["Sessions"],
        name="Sessions", mode="lines",
        line=dict(color="#a855f7", width=2),
        fill="tozeroy", fillcolor="rgba(168,85,247,0.08)"
    ))
    if "Users" in df_f.columns:
        fig1.add_trace(go.Scatter(
            x=df_f["Date"], y=df_f["Users"],
            name="Users", mode="lines",
            line=dict(color="#22d3ee", width=1.5, dash="dot")
        ))
    apply_layout(fig1)
    fig1.update_layout(height=340, xaxis_title="Date", yaxis_title="Count")
    st.plotly_chart(fig1, use_container_width=True)

    # Monthly bar
    st.markdown('<div class="section-header">Monthly Session Volume</div>', unsafe_allow_html=True)
    df_monthly = df_f.copy()
    df_monthly["Month"] = df_monthly["Date"].dt.to_period("M").astype(str)
    monthly = df_monthly.groupby("Month")["Sessions"].sum().reset_index()

    fig_bar = go.Figure(go.Bar(
        x=monthly["Month"], y=monthly["Sessions"],
        marker=dict(
            color=monthly["Sessions"],
            colorscale=[[0,"#3b0764"],[0.5,"#7c3aed"],[1,"#22d3ee"]],
            showscale=False
        )
    ))
    apply_layout(fig_bar)
    fig_bar.update_layout(height=280, xaxis_tickangle=-45, yaxis_title="Sessions")
    st.plotly_chart(fig_bar, use_container_width=True)

    # Source breakdown
    if "Source / Medium" in df_f.columns:
        st.markdown('<div class="section-header">Traffic by Source / Medium</div>', unsafe_allow_html=True)
        src_data = df_f.groupby("Source / Medium")["Sessions"].sum().sort_values(ascending=False).reset_index()

        c1, c2 = st.columns([1, 1])
        with c1:
            fig_pie = go.Figure(go.Pie(
                labels=src_data["Source / Medium"],
                values=src_data["Sessions"],
                hole=0.55,
                marker=dict(colors=SOURCE_COLORS),
                textfont=dict(size=11)
            ))
            apply_layout(fig_pie, "Traffic Share by Source")
            fig_pie.update_layout(height=320, showlegend=True,
                legend=dict(orientation="v", x=1.02, font=dict(size=10)))
            st.plotly_chart(fig_pie, use_container_width=True)

        with c2:
            fig_hbar = go.Figure(go.Bar(
                x=src_data["Sessions"],
                y=src_data["Source / Medium"],
                orientation="h",
                marker=dict(color=SOURCE_COLORS[:len(src_data)])
            ))
            apply_layout(fig_hbar, "Sessions by Source")
            fig_hbar.update_layout(height=320, yaxis=dict(autorange="reversed"),
                                   xaxis_title="Sessions")
            st.plotly_chart(fig_hbar, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Forecast
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-header">Time-Series Forecast (Holt-Winters)</div>', unsafe_allow_html=True)
    st.caption("Exponential smoothing with trend + weekly seasonality decomposition")

    try:
        forecast, model = run_forecast(df, periods=forecast_days)

        split_str = df["Date"].max().strftime("%Y-%m-%d")

        fig_fc = go.Figure()
        fig_fc.add_trace(go.Scatter(
            x=df["Date"], y=df["Sessions"],
            name="Actual", mode="lines",
            line=dict(color="#a855f7", width=2)
        ))
        fig_fc.add_trace(go.Scatter(
            x=forecast["ds"], y=forecast["yhat"],
            name="Forecast", mode="lines",
            line=dict(color="#f59e0b", width=2, dash="dash")
        ))
        fig_fc.add_trace(go.Scatter(
            x=forecast["ds"], y=forecast["yhat_upper"],
            fill=None, mode="lines",
            line=dict(width=0), showlegend=False
        ))
        fig_fc.add_trace(go.Scatter(
            x=forecast["ds"], y=forecast["yhat_lower"],
            fill="tonexty", mode="lines",
            line=dict(width=0),
            fillcolor="rgba(245,158,11,0.10)",
            name="Confidence Band"
        ))
        fig_fc.add_shape(type="line",
            x0=split_str, x1=split_str,
            y0=0, y1=1, yref="paper",
            line=dict(color="#22d3ee", dash="dot", width=1.5)
        )
        fig_fc.add_annotation(
            x=split_str, y=1, yref="paper",
            text="Forecast Start",
            font=dict(color="#22d3ee", size=11),
            showarrow=False, yshift=10
        )
        apply_layout(fig_fc)
        fig_fc.update_layout(height=380, xaxis_title="Date", yaxis_title="Sessions")
        st.plotly_chart(fig_fc, use_container_width=True)

        st.markdown(f'<div class="section-header">Next {forecast_days} Days Prediction</div>', unsafe_allow_html=True)
        future_only = forecast[forecast["ds"] > df["Date"].max()]

        fig_fut = go.Figure()
        fig_fut.add_trace(go.Scatter(
            x=future_only["ds"], y=future_only["yhat_upper"],
            fill=None, mode="lines",
            line=dict(width=0), showlegend=False
        ))
        fig_fut.add_trace(go.Scatter(
            x=future_only["ds"], y=future_only["yhat_lower"],
            fill="tonexty", mode="lines",
            line=dict(width=0),
            fillcolor="rgba(52,211,153,0.12)",
            name="Confidence Band"
        ))
        fig_fut.add_trace(go.Scatter(
            x=future_only["ds"], y=future_only["yhat"],
            name="Predicted", mode="lines+markers",
            line=dict(color="#34d399", width=2.5),
            marker=dict(size=4)
        ))
        apply_layout(fig_fut)
        fig_fut.update_layout(height=320, xaxis_title="Date", yaxis_title="Sessions")
        st.plotly_chart(fig_fut, use_container_width=True)

        st.markdown('<div class="section-header">Trend Decomposition</div>', unsafe_allow_html=True)
        fig_trend = go.Figure(go.Scatter(
            x=forecast["ds"], y=forecast["trend"],
            mode="lines", line=dict(color="#c084fc", width=2)
        ))
        apply_layout(fig_trend, "Overall Trend")
        fig_trend.update_layout(height=240)
        st.plotly_chart(fig_trend, use_container_width=True)

        from sklearn.metrics import mean_absolute_error, mean_squared_error
        hist = forecast[forecast["ds"].isin(df["Date"])]
        if len(hist) > 0:
            mae = mean_absolute_error(df["Sessions"].values[:len(hist)], hist["yhat"].values)
            rmse = np.sqrt(mean_squared_error(df["Sessions"].values[:len(hist)], hist["yhat"].values))
            m1, m2 = st.columns(2)
            m1.metric("MAE", f"{mae:,.0f} sessions")
            m2.metric("RMSE", f"{rmse:,.0f} sessions")

    except Exception as e:
        st.error(f"Forecast error: {e}")
        import traceback
        st.code(traceback.format_exc())


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Geography
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-header">Traffic by Country</div>', unsafe_allow_html=True)

    country_df = get_countries(df_f)

    # Choropleth world map
    fig_map = px.choropleth(
        country_df,
        locations="Country",
        locationmode="country names",
        color="Sessions",
        hover_name="Country",
        hover_data={"Conversions": True, "Conversion Rate": True},
        color_continuous_scale=[[0,"#1e1b4b"],[0.3,"#4c1d95"],[0.6,"#7c3aed"],[1,"#c084fc"]],
    )
    fig_map.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        geo=dict(
            bgcolor="rgba(16,16,42,0.9)",
            lakecolor="rgba(16,16,42,0.9)",
            landcolor="rgba(40,30,80,0.8)",
            showframe=False,
            showcoastlines=True,
            coastlinecolor="rgba(124,58,237,0.4)",
        ),
        font=dict(color="#f1f0ff"),
        coloraxis_colorbar=dict(
            title=dict(text="Sessions", font=dict(color="#c084fc")),
            tickfont=dict(color="#f1f0ff"),
        ),
        height=380,
        margin=dict(l=0, r=0, t=20, b=0)
    )
    st.plotly_chart(fig_map, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="section-header">Sessions by Country</div>', unsafe_allow_html=True)
        fig_ctry = go.Figure(go.Bar(
            x=country_df["Sessions"],
            y=country_df["Country"],
            orientation="h",
            marker=dict(
                color=country_df["Sessions"],
                colorscale=[[0,"#4c1d95"],[1,"#22d3ee"]],
                showscale=False
            ),
            text=country_df["Sessions"].apply(lambda x: f"{x:,}"),
            textposition="outside",
            textfont=dict(color="#f1f0ff", size=10)
        ))
        apply_layout(fig_ctry)
        fig_ctry.update_layout(height=360, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_ctry, use_container_width=True)

    with c2:
        st.markdown('<div class="section-header">Conversion Rate by Country</div>', unsafe_allow_html=True)
        fig_cvr = go.Figure(go.Bar(
            x=country_df["Conversion Rate"],
            y=country_df["Country"],
            orientation="h",
            marker=dict(
                color=country_df["Conversion Rate"],
                colorscale=[[0,"#4c1d95"],[1,"#34d399"]],
                showscale=False
            ),
            text=country_df["Conversion Rate"].apply(lambda x: f"{x:.2f}%"),
            textposition="outside",
            textfont=dict(color="#f1f0ff", size=10)
        ))
        apply_layout(fig_cvr)
        fig_cvr.update_layout(height=360, yaxis=dict(autorange="reversed"), xaxis_title="Conv. Rate %")
        st.plotly_chart(fig_cvr, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Peak Hours
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown('<div class="section-header">Hourly Traffic Heatmap (Last 90 Days)</div>', unsafe_allow_html=True)
    st.caption("Which hour × day combinations drive the most traffic")

    with st.spinner("Generating hourly breakdown..."):
        hourly_df = get_hourly(df_f)

        # Pivot for heatmap
        day_order = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
        pivot = hourly_df.groupby(["day_of_week","hour"])["sessions"].mean().reset_index()
        pivot_wide = pivot.pivot(index="day_of_week", columns="hour", values="sessions").reindex(day_order)

        fig_heat = go.Figure(go.Heatmap(
            z=pivot_wide.values,
            x=[f"{h:02d}:00" for h in range(24)],
            y=day_order,
            colorscale=[[0,"#0f0f2d"],[0.3,"#4c1d95"],[0.6,"#7c3aed"],[0.85,"#c084fc"],[1,"#22d3ee"]],
            hoverongaps=False,
            hovertemplate="<b>%{y} %{x}</b><br>Avg Sessions: %{z:.0f}<extra></extra>"
        ))
        apply_layout(fig_heat)
        fig_heat.update_layout(
            height=320,
            xaxis=dict(tickangle=-45, tickfont=dict(size=10)),
            yaxis=dict(tickfont=dict(size=11)),
            coloraxis_showscale=True
        )
        st.plotly_chart(fig_heat, use_container_width=True)

        # Peak hour bar
        st.markdown('<div class="section-header">Average Sessions by Hour of Day</div>', unsafe_allow_html=True)
        hourly_avg = hourly_df.groupby("hour")["sessions"].mean().reset_index()
        peak_hour = int(hourly_avg.loc[hourly_avg["sessions"].idxmax(), "hour"])

        fig_hh = go.Figure(go.Bar(
            x=[f"{h:02d}:00" for h in hourly_avg["hour"]],
            y=hourly_avg["sessions"],
            marker=dict(
                color=hourly_avg["sessions"],
                colorscale=[[0,"#3b0764"],[0.5,"#7c3aed"],[1,"#22d3ee"]],
                showscale=False
            )
        ))
        fig_hh.add_shape(type="line",
            x0=peak_hour, x1=peak_hour,
            y0=0, y1=1, yref="paper",
            line=dict(color="#34d399", dash="dash", width=2)
        )
        fig_hh.add_annotation(
            x=peak_hour, y=1, yref="paper",
            text=f"🔥 Peak: {peak_hour:02d}:00",
            font=dict(color="#34d399"), showarrow=False, yshift=10
        )
        apply_layout(fig_hh)
        fig_hh.update_layout(height=280, xaxis_title="Hour", yaxis_title="Avg Sessions")
        st.plotly_chart(fig_hh, use_container_width=True)

        # Insight cards
        peak_day = pivot_wide.mean(axis=1).idxmax()
        peak_h_val = int(hourly_avg["sessions"].max())
        ic1, ic2, ic3 = st.columns(3)
        ic1.metric("🔥 Peak Hour", f"{peak_hour:02d}:00 - {peak_hour+1:02d}:00")
        ic2.metric("📅 Busiest Day", peak_day)
        ic3.metric("Avg Peak Sessions/hr", f"{peak_h_val:,}")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5 — Conversions
# ═══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown('<div class="section-header">Conversion Rate Over Time</div>', unsafe_allow_html=True)

    if "Conversion Rate" in df_f.columns and "Conversions" in df_f.columns:
        # 7-day rolling avg
        df_cvr = df_f[["Date","Sessions","Conversions","Conversion Rate"]].copy()
        df_cvr["CVR_7d"] = df_cvr["Conversion Rate"].rolling(7, min_periods=1).mean()

        fig_cvr_line = go.Figure()
        fig_cvr_line.add_trace(go.Scatter(
            x=df_cvr["Date"], y=df_cvr["Conversion Rate"],
            name="Daily CVR", mode="lines",
            line=dict(color="rgba(52,211,153,0.35)", width=1)
        ))
        fig_cvr_line.add_trace(go.Scatter(
            x=df_cvr["Date"], y=df_cvr["CVR_7d"],
            name="7-Day Rolling Avg", mode="lines",
            line=dict(color="#34d399", width=2.5)
        ))
        apply_layout(fig_cvr_line)
        fig_cvr_line.update_layout(height=320, xaxis_title="Date", yaxis_title="Conversion Rate %")
        st.plotly_chart(fig_cvr_line, use_container_width=True)

        # Sessions vs Conversions
        st.markdown('<div class="section-header">Sessions vs Conversions (Monthly)</div>', unsafe_allow_html=True)
        df_cvr["Month"] = df_cvr["Date"].dt.to_period("M").astype(str)
        monthly_cvr = df_cvr.groupby("Month").agg({"Sessions":"sum","Conversions":"sum"}).reset_index()

        fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
        fig_dual.add_trace(go.Bar(
            x=monthly_cvr["Month"], y=monthly_cvr["Sessions"],
            name="Sessions", marker_color="rgba(124,58,237,0.6)"
        ), secondary_y=False)
        fig_dual.add_trace(go.Scatter(
            x=monthly_cvr["Month"], y=monthly_cvr["Conversions"],
            name="Conversions", mode="lines+markers",
            line=dict(color="#34d399", width=2.5),
            marker=dict(size=6)
        ), secondary_y=True)
        fig_dual.update_layout(**PLOT_LAYOUT)
        fig_dual.update_layout(height=320, xaxis_tickangle=-45)
        fig_dual.update_yaxes(title_text="Sessions", secondary_y=False,
                              gridcolor="rgba(124,58,237,0.12)")
        fig_dual.update_yaxes(title_text="Conversions", secondary_y=True,
                              gridcolor="rgba(124,58,237,0.05)")
        st.plotly_chart(fig_dual, use_container_width=True)

        # Source CVR comparison
        if "Source / Medium" in df_f.columns:
            st.markdown('<div class="section-header">Conversion Rate by Source</div>', unsafe_allow_html=True)
            src_cvr = df_f.groupby("Source / Medium").agg(
                Sessions=("Sessions","sum"),
                Conversions=("Conversions","sum")
            ).reset_index()
            src_cvr["CVR"] = (src_cvr["Conversions"] / src_cvr["Sessions"].replace(0,1) * 100).round(2)
            src_cvr = src_cvr.sort_values("CVR", ascending=True)

            fig_src_cvr = go.Figure(go.Bar(
                x=src_cvr["CVR"],
                y=src_cvr["Source / Medium"],
                orientation="h",
                marker=dict(
                    color=src_cvr["CVR"],
                    colorscale=[[0,"#4c1d95"],[1,"#34d399"]],
                    showscale=False
                ),
                text=src_cvr["CVR"].apply(lambda x: f"{x:.2f}%"),
                textposition="outside",
                textfont=dict(color="#f1f0ff", size=10)
            ))
            apply_layout(fig_src_cvr)
            fig_src_cvr.update_layout(height=320, xaxis_title="Conversion Rate %")
            st.plotly_chart(fig_src_cvr, use_container_width=True)

    else:
        st.info("⚠️ Conversion data not found in dataset. Upload GA4 CSV with 'Conversions' column or use generated sample data.")
        if st.button("🔄 Regenerate sample data with conversions"):
            if os.path.exists("data/traffic.csv"):
                os.remove("data/traffic.csv")
            st.cache_data.clear()
            st.rerun()

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<div style="text-align:center;color:#4a4870;font-size:0.75rem;font-family:JetBrains Mono,monospace">'
    'TrafficLens · Built with Prophet (Meta) · Streamlit · Plotly · Python 3.8'
    '</div>',
    unsafe_allow_html=True
)