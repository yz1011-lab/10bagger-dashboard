"""
10-Bagger v2 — 知識庫管理頁 (NotebookLM Sources)
Display, add, and manage notebook_sources per stock.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from utils.supabase_client import (
    get_supabase,
    fetch_active_stocks,
    fetch_notebook_sources,
    update_notebook_source_status,
)
from utils.constants import NOTEBOOKLM_BASE, DRIVE_FOLDERS

st.set_page_config(page_title="知識庫管理 | 10-Bagger", page_icon="📚", layout="wide")
st.markdown("## 📚 知識庫管理 (NotebookLM Sources)")

# ── Load data ─────────────────────────────────────────────────
stocks = fetch_active_stocks()
all_sources = fetch_notebook_sources()

if not stocks:
    st.warning("尚無追蹤股票。")
    st.stop()

# ── KPI metrics ───────────────────────────────────────────────
active_sources = [s for s in all_sources if s.get("status") != "deleted"]
col1, col2, col3, col4 = st.columns(4)
col1.metric("總資料來源數", len(active_sources))
col2.metric("追蹤股票數", len(stocks))

# Sources per stock
sources_by_stock = {}
for s in active_sources:
    t = s.get("ticker", "unknown")
    sources_by_stock[t] = sources_by_stock.get(t, 0) + 1
avg_per_stock = len(active_sources) / len(stocks) if stocks else 0
col3.metric("平均每股來源數", f"{avg_per_stock:.1f}")

latest_src = active_sources[0]["created_at"][:10] if active_sources else "—"
col4.metric("最近新增日期", latest_src)

st.divider()

# ── Quick links ───────────────────────────────────────────────
link_col1, link_col2 = st.columns(2)
with link_col1:
    notebook_id = st.secrets.get("notebooklm", {}).get("notebook_id", "")
    if notebook_id:
        nb_url = f"{NOTEBOOKLM_BASE}/{notebook_id}"
        st.link_button("📓 開啟 NotebookLM", nb_url, use_container_width=True)
    else:
        st.caption("未設定 NotebookLM notebook_id")
with link_col2:
    drive_url = f"https://drive.google.com/drive/folders/{DRIVE_FOLDERS['02_stocks']}"
    st.link_button("📁 Google Drive 個股研究", drive_url, use_container_width=True)

st.divider()

# ── Per-stock source management ───────────────────────────────
st.markdown("### 📂 各股票知識庫來源")

tickers = [s["ticker"] for s in stocks]

# Show sources grouped by stock
tab_list = st.tabs(tickers)

for i, ticker in enumerate(tickers):
    with tab_list[i]:
        stock_sources = fetch_notebook_sources(ticker)
        active = [s for s in stock_sources if s.get("status") != "deleted"]

        st.markdown(f"**{ticker}** — {len(active)} 筆資料來源")

        if active:
            for src in active:
                col_info, col_actions = st.columns([4, 1])
                with col_info:
                    title = src.get("title", "未命名")
                    src_type = src.get("source_type", "—")
                    added_by = src.get("added_by", "—")
                    created = src.get("created_at", "")[:16]
                    status = src.get("status", "active")

                    status_icon = {"active": "🟢", "important": "⭐", "archived": "📦"}.get(status, "⚪")
                    st.markdown(f"{status_icon} **{title}**  \n`{src_type}` · {added_by} · {created}")

                with col_actions:
                    src_id = src.get("id")
                    key_prefix = f"{ticker}_{src_id}"

                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        if st.button("⭐", key=f"imp_{key_prefix}", help="標記重要"):
                            update_notebook_source_status(src_id, "important")
                            st.rerun()
                    with col_b:
                        if st.button("📦", key=f"arch_{key_prefix}", help="封存"):
                            update_notebook_source_status(src_id, "archived")
                            st.rerun()
                    with col_c:
                        if st.button("🗑️", key=f"del_{key_prefix}", help="刪除"):
                            update_notebook_source_status(src_id, "deleted")
                            st.rerun()

            # Source type breakdown
            types = [s.get("source_type", "unknown") for s in active]
            type_counts = pd.Series(types).value_counts()
            st.markdown("**類型分布：** " + " · ".join(f"{t}: {c}" for t, c in type_counts.items()))
        else:
            st.caption("此股票尚無知識庫來源。")

st.divider()

# ── Add new source ────────────────────────────────────────────
st.markdown("### ➕ 新增資料來源")

with st.form("add_source_form", clear_on_submit=True):
    fc1, fc2 = st.columns(2)
    with fc1:
        new_ticker = st.selectbox("股票", tickers, key="new_src_ticker")
        new_title = st.text_input("標題", placeholder="例：Q4 2025 財報分析")
    with fc2:
        new_type = st.selectbox("來源類型", ["research_report", "earnings", "news", "analyst_note", "sec_filing", "custom"])
        new_added_by = st.text_input("新增者", value="manual")

    new_url = st.text_input("來源 URL（選填）", placeholder="https://...")

    submitted = st.form_submit_button("新增來源", use_container_width=True)
    if submitted:
        if not new_title:
            st.error("請填寫標題。")
        else:
            sb = get_supabase()
            payload = {
                "ticker": new_ticker,
                "title": new_title,
                "source_type": new_type,
                "added_by": new_added_by,
                "status": "active",
                "source_url": new_url or None,
            }
            try:
                sb.table("notebook_sources").insert(payload).execute()
                st.success(f"已新增來源「{new_title}」至 {new_ticker}")
                st.rerun()
            except Exception as e:
                st.error(f"新增失敗：{e}")

st.divider()

# ── Full source table ─────────────────────────────────────────
st.markdown("### 📋 全部資料來源")

filter_status = st.multiselect(
    "篩選狀態",
    ["active", "important", "archived", "deleted"],
    default=["active", "important"],
)

filtered = [s for s in all_sources if s.get("status", "active") in filter_status]

if filtered:
    df = pd.DataFrame(filtered)
    display_cols = ["ticker", "title", "source_type", "added_by", "status", "created_at"]
    available_cols = [c for c in display_cols if c in df.columns]
    df_display = df[available_cols].copy()
    df_display.columns = ["股票", "標題", "類型", "新增者", "狀態", "建立時間"][:len(available_cols)]
    st.dataframe(df_display, use_container_width=True, hide_index=True, height=400)
else:
    st.info("無符合條件的資料來源。")
