import streamlit as st
import pandas as pd
import json
import time

st.set_page_config(page_title="Phoenix AI Workflow Scheduler", layout="wide", page_icon="🦅")

# Custom CSS for dark mode hacking aesthetic
st.markdown("""
<style>
    .metric-card {
        background-color: #1E1E1E;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #00FF00;
        margin-bottom: 20px;
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        color: #00FF00;
    }
    .metric-label {
        color: #A0A0A0;
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🦅 Phoenix: Carbon & Latency-Aware Workflow Scheduler")
st.markdown("Live Autonomous CI/CD Self-Healing Dashboard")

@st.cache_data(ttl=1)
def load_data():
    try:
        with open("telemetry.jsonl", "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        data = []
        for line in lines:
            if not line.strip(): continue
            try:
                record = json.loads(line)
                
                # Expand nested state_diff and metrics if they exist
                diff = record.get("state_diff", {})
                metrics = diff.get("telemetry", {})
                
                row = {
                    "timestamp": pd.to_datetime(record.get("timestamp", time.time()), unit="s"),
                    "node": record.get("node", "unknown"),
                    "route": record.get("route", "unknown"),
                    "latency_ms": record.get("latency_ms", 0),
                    "gco2": record.get("gco2", 0.0),
                    "cost_usd": record.get("cost_usd", 0.0),
                    "selected_model": diff.get("selected_model", "qwen2.5-coder:7b"),
                    "bug_type": diff.get("bug_type", "unknown"),
                    "rag_status": diff.get("rag_status", "unknown"),
                    "local_grid": metrics.get("local_grid", 0),
                    "cloud_grid": metrics.get("cloud_grid", 0),
                    "local_emissions": metrics.get("local_emissions_gCO2", 0.0),
                    "cloud_emissions": metrics.get("cloud_emissions_gCO2", 0.0),
                }
                data.append(row)
            except Exception:
                continue
        return pd.DataFrame(data)
    except FileNotFoundError:
        return pd.DataFrame()

# Auto-refresh loop container
placeholder = st.empty()

with placeholder.container():
    df = load_data()
    
    if df.empty:
        st.warning("Waiting for telemetry data in `telemetry.jsonl`...")
    else:
        # Calculate high-level metrics
        total_carbon_saved = 0.0
        
        # Only look at scheduler_entry_node events for routing metrics
        scheduler_events = df[df["node"] == "scheduler_entry_node"]
        
        if not scheduler_events.empty:
            for _, row in scheduler_events.iterrows():
                # If local_emissions > cloud_emissions and we picked cloud, we saved carbon!
                # If cloud > local and we picked local, we saved carbon!
                worst = max(row["local_emissions"], row["cloud_emissions"])
                actual = row["local_emissions"] if row["route"] == "local_edge" else row["cloud_emissions"]
                if worst > 0:
                    total_carbon_saved += (worst - actual)
                    
            route_counts = scheduler_events["route"].value_counts()
            model_counts = scheduler_events["selected_model"].value_counts()
        else:
            route_counts = pd.Series({"local_edge": 0, "cloud_heavy": 0})
            model_counts = pd.Series()

        # Top row metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Total Jobs Processed</div><div class="metric-value">{len(scheduler_events)}</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Estimated Carbon Saved</div><div class="metric-value">{total_carbon_saved:.2f} gCO₂</div></div>', unsafe_allow_html=True)
        with col3:
            recent_local_grid = scheduler_events["local_grid"].iloc[-1] if not scheduler_events.empty else 0
            st.markdown(f'<div class="metric-card"><div class="metric-label">Live Grid (Local)</div><div class="metric-value">{recent_local_grid} gCO₂/kWh</div></div>', unsafe_allow_html=True)
        with col4:
            rag_events = df[df["node"] == "rag"]
            hit_rate = 0
            if not rag_events.empty:
                hits = len(rag_events[rag_events["rag_status"] == "ok"])
                hit_rate = (hits / len(rag_events)) * 100
            st.markdown(f'<div class="metric-card"><div class="metric-label">RAG Hit Rate</div><div class="metric-value">{hit_rate:.1f}%</div></div>', unsafe_allow_html=True)

        # Charts row
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.subheader("Execution Routing")
            if not route_counts.empty:
                st.bar_chart(route_counts, color="#00FF00")
            else:
                st.info("No routing data yet.")
                
        with col_chart2:
            st.subheader("Dynamic Model Selection")
            if not model_counts.empty:
                st.bar_chart(model_counts, color="#00BFFF")
            else:
                st.info("No model data yet.")
                
        st.subheader("Recent Workflow Events")
        display_cols = ["timestamp", "node", "route", "selected_model", "latency_ms"]
        st.dataframe(df[display_cols].tail(10).sort_values("timestamp", ascending=False), use_container_width=True)

# Note: Streamlit usually uses st.rerun() but we're keeping it simple for the script. 
# Run via: streamlit run dashboard.py
