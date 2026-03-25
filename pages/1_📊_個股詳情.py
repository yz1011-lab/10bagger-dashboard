"""
10-Bagger v2 — 個股詳情頁
Includes NotebookLM knowledge base links and source statistics.
"""

import streamlit as st
import pandas as pd

from utils.supabase_client import (
    fetch_active_stocks,
    fetch_stock_probabilities,
    fetch_probability_log,
    fetch_evidence_log,
    fetch_notebook_sources,
)
from utils.charts import probability_gauge, probability_history_line
from utils.constants import (
    PH_ELIMINATION,
    PH_HIGH_PROBABILITY,
    ALERT_LABELS,
    NOTEBOOKLM_BASE,
    DRIVE_FOLDERS,
)

st.set_page_config(page_title="個股詳情 | 10-Bagger", page_icon="📊", layout="wide")
st.markdown("## 📊 個股詳情")

# ── Stock selector ───────────────────────────────────────────
stocks = fetch_active_stocks()
probs = fetch_stock_probabilities()
prob_map = {p["stock_ticker"]: p for p in probs}

if not stocks:
    st.warning("尚無追蹤股票。")
    st.stop()

tickers = [s["ticker"] for s in stocks]
selected = st.selectbox("選擇股票", tickers, index=0)

stock_info = next((s for s in stocks if s["ticker"] == selected), {})
prob_info = prob_map.get(selected, {})
current_ph = prob_info.get("current_ph", 0.15)

# ── Header section ───────────────────────────────────────────
col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    fig_g = probability_gauge(selected, current_ph)
    st.plotly_chart(fig_g, use_container_width=True)

with col2:
    st.markdown(f"### {selected} — {stock_info.get('name', '')}")
    st.markdown(f"**市場：** {stock_info.get('market', '—')}")
    st.markdown(f"**P(H)：** {current_ph:.1%}")
    st.markdown(f"**累計更新：** {prob_info.get('total_updates', 0)} 次")

    # Alert badge
    if current_ph < PH_ELIMINATION:
        st.error("⚠️ 低於淘汰線 (5%) — 建議檢視持倉")
    elif current_ph >= PH_HIGH_PROBABILITY:
        st.success("🔥 高機率十倍股候選 (>50%)")
    else:
        st.info(f"📈 一般觀察中 ({current_ph:.1%})")

with col3:
    # NotebookLM link
    notebook_id = st.secrets.get("notebooklm", {}).get("notebook_id", "")
    if notebook_id:
        nb_url = f"{NOTEBOOKLM_BASE}/{notebook_id}"
        st.link_button("📓 開啟 NotebookLM", nb_url, use_container_width=True)

    # Google Drive link
    drive_url = f"https://drive.google.com/drive/folders/{DRIVE_FOLDERS['02_stocks']}"
    st.link_button("📁 Google Drive 個股研究", drive_url, use_container_width=True)

st.divider()

# ── NotebookLM Sources stats ─────────────────────────────────
st.markdown("### 📚 知識庫資料來源")

sources = fetch_notebook_sources(selected)
active_sources = [s for s in sources if s.get("status") != "deleted"]

col_a, col_b, col_c = st.columns(3)
col_a.metric("資料來源數", len(active_sources))
col_b.metric("最近更新", active_sources[0]["created_at"][:10] if active_sources else "—")
col_c.metric("類型分布", ", ".join(set(s.get("source_type", "?") for s in active_sources[:5])) or "—")

if active_sources:
    df_src = pd.DataFrame(active_sources)[["title", "source_type", "added_by", "created_at", "status"]]
    df_src.columns = ["標題", "類型", "新增者", "時間", "狀態"]
    st.dataframe(df_src, use_container_width=True, hide_index=True, height=200)
else:
    st.caption("此股票尚無知識庫來源。")

st.divider()

# ── P(H) history ─────────────────────────────────────────────
st.markdown("### 📈 P(H) 歷史走勢")

log_data = fetch_probability_log(selected, limit=100)
if log_data:
    df_log = pd.DataFrame(log_data)
    df_log["created_at"] = pd.to_datetime(df_log["created_at"])
    fig = probability_history_line(df_log, selected)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("此股票尚無 P(H) 更新記錄。")

st.divider()

# ── Evidence log ─────────────────────────────────────────────
st.markdown("### 🔍 證據記錄")

evidence = fetch_evidence_log(selected, limit=50)
if evidence:
    for ev in evidence[:10]:
        with st.expander(f"📌 {ev.get('created_at', '')[:16]} — {ev.get('source_type', '')}"):
            st.markdown(f"**來源：** {ev.get('source_url', '—')}")
            st.markdown(f"**摘要：** {ev.get('summary', '—')}")
            if ev.get("key_findings"):
                st.markdown(f"**關鍵發現：** {ev['key_findings']}")
else:
    st.info("此股票尚無證據記錄。")

# ── Probability log detail ───────────────────────────────────
if log_data:
    st.divider()
    st.markdown("### 📋 貝葉斯更新明細")

    for entry in log_data[:5]:
        alert = entry.get("alert_type", "none")
        label, color = ALERT_LABELS.get(alert, ("—", "gray"))

        with st.expander(
            f"{'🔴' if 'low' in alert else '🟢' if 'high' in alert else '⚪'} "
            f"{entry.get('created_at', '')[:16]} — "
            f"P(H) {entry.get('prior_ph', 0):.2%} → {entry.get('new_ph', 0):.2%}"
        ):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Bull P(E|H):** {entry.get('pe_h_bull', 0):.3f}")
                st.markdown(f"**Bear P(E|H):** {entry.get('pe_h_bear', 0):.3f}")
                st.markdown(f"**Final P(E|H):** {entry.get('final_pe_h', 0):.3f}")
            with c2:
                st.markdown(f"**Bull P(E|¬H):** {entry.get('pe_not_h_bull', 0):.3f}")
                st.markdown(f"**Bear P(E|¬H):** {entry.get('pe_not_h_bear', 0):.3f}")
                st.markdown(f"**Final P(E|¬H):** {entry.get('final_pe_not_h', 0):.3f}")

            st.markdown(f"**信心度：** {entry.get('confidence', 0):.0%}")
            st.markdown(f"**警報：** {label}")
            if entry.get("judge_ruling"):
                st.markdown(f"**裁判裁定：** {entry['judge_ruling'][:200]}")
