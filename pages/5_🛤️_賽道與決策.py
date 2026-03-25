"""
10-Bagger v2 — 賽道與決策信箱
Tracks confidence overview + Decision Inbox management.
"""

import streamlit as st
import pandas as pd

from utils.supabase_client import (
    fetch_tracks,
    fetch_decisions_inbox,
    get_supabase,
)
from utils.charts import track_confidence_bar
from utils.constants import CONSENSUS_COLORS

st.set_page_config(page_title="賽道與決策 | 10-Bagger", page_icon="🛤️", layout="wide")
st.markdown("## 🛤️ 賽道與決策信箱")

# ══════════════════════════════════════════════════════════════
# Part 1: Tracks
# ══════════════════════════════════════════════════════════════
st.markdown("### 🛤️ 賽道信心指數")

tracks = fetch_tracks()

if tracks:
    col_chart, col_detail = st.columns([3, 2])

    with col_chart:
        fig = track_confidence_bar(tracks)
        st.plotly_chart(fig, use_container_width=True)

    with col_detail:
        for t in tracks:
            name = t.get("name", "—")
            confidence = t.get("confidence", 0)
            consensus = t.get("consensus_level", "moderate")
            emoji = {"high": "🟢", "moderate": "🟡", "contrarian": "🔴"}.get(consensus, "⚪")
            color = CONSENSUS_COLORS.get(consensus, "#888")

            st.markdown(
                f"**{emoji} {name}**  \n"
                f"信心 {confidence:.0f}% · 共識 {consensus}"
            )
            if t.get("description"):
                st.caption(t["description"][:100])
            st.markdown("---")

    # Track table
    st.markdown("#### 📋 賽道一覽")
    df_tracks = pd.DataFrame(tracks)
    display_cols = ["name", "confidence", "consensus_level"]
    available = [c for c in display_cols if c in df_tracks.columns]
    if available:
        df_disp = df_tracks[available].copy()
        df_disp.columns = ["賽道名稱", "信心指數", "共識程度"][:len(available)]
        st.dataframe(df_disp, use_container_width=True, hide_index=True)
else:
    st.info("尚無賽道資料。")

st.divider()

# ══════════════════════════════════════════════════════════════
# Part 2: Decision Inbox
# ══════════════════════════════════════════════════════════════
st.markdown("### 📬 決策信箱")

# Status filter
status_filter = st.radio(
    "篩選狀態",
    ["pending", "approved", "rejected", "all"],
    format_func=lambda x: {
        "pending": "⏳ 待處理",
        "approved": "✅ 已通過",
        "rejected": "❌ 已駁回",
        "all": "📋 全部",
    }.get(x, x),
    horizontal=True,
)

inbox = fetch_decisions_inbox(status=status_filter if status_filter != "all" else None)

if inbox:
    # KPIs
    col_k1, col_k2, col_k3 = st.columns(3)
    all_inbox = fetch_decisions_inbox()
    pending_count = sum(1 for d in all_inbox if d.get("status") == "pending")
    approved_count = sum(1 for d in all_inbox if d.get("status") == "approved")
    col_k1.metric("待處理", pending_count)
    col_k2.metric("已通過", approved_count)
    col_k3.metric("目前顯示", len(inbox))

    for item in inbox:
        item_id = item.get("id", "")
        ticker = item.get("stock_ticker", item.get("stock_id", "—"))
        decision_type = item.get("decision_type", item.get("type", "—"))
        status = item.get("status", "pending")
        created = item.get("created_at", "")[:16]

        status_icon = {"pending": "⏳", "approved": "✅", "rejected": "❌"}.get(status, "⚪")

        with st.expander(f"{status_icon} {created} — {ticker} · {decision_type}"):
            st.markdown(f"**股票：** {ticker}")
            st.markdown(f"**類型：** {decision_type}")
            st.markdown(f"**狀態：** {status}")

            if item.get("summary"):
                st.markdown(f"**摘要：** {item['summary'][:300]}")
            if item.get("recommendation"):
                st.markdown(f"**建議：** {item['recommendation'][:300]}")
            if item.get("reasoning"):
                st.markdown(f"**理由：** {item['reasoning'][:300]}")

            # Action buttons for pending items
            if status == "pending":
                bcol1, bcol2, bcol3 = st.columns(3)
                with bcol1:
                    if st.button("✅ 通過", key=f"approve_{item_id}"):
                        sb = get_supabase()
                        try:
                            sb.table("decisions_inbox").update(
                                {"status": "approved"}
                            ).eq("id", item_id).execute()
                            st.success("已通過")
                            st.rerun()
                        except Exception as e:
                            st.error(f"操作失敗：{e}")
                with bcol2:
                    if st.button("❌ 駁回", key=f"reject_{item_id}"):
                        sb = get_supabase()
                        try:
                            sb.table("decisions_inbox").update(
                                {"status": "rejected"}
                            ).eq("id", item_id).execute()
                            st.success("已駁回")
                            st.rerun()
                        except Exception as e:
                            st.error(f"操作失敗：{e}")
                with bcol3:
                    if st.button("📌 標記跟進", key=f"flag_{item_id}"):
                        st.info("跟進功能開發中。")

    # Full table view
    st.markdown("#### 📋 決策列表")
    df_inbox = pd.DataFrame(inbox)
    display_cols = ["stock_ticker", "decision_type", "status", "created_at"]
    # Try alternate column names
    if "stock_ticker" not in df_inbox.columns and "stock_id" in df_inbox.columns:
        df_inbox["stock_ticker"] = df_inbox["stock_id"]
    if "decision_type" not in df_inbox.columns and "type" in df_inbox.columns:
        df_inbox["decision_type"] = df_inbox["type"]
    available = [c for c in display_cols if c in df_inbox.columns]
    if available:
        df_disp = df_inbox[available].copy()
        col_labels = ["股票", "決策類型", "狀態", "時間"]
        df_disp.columns = col_labels[:len(available)]
        st.dataframe(df_disp, use_container_width=True, hide_index=True)
else:
    st.info("無符合條件的決策項目。")

# ── Footer ────────────────────────────────────────────────────
st.divider()
st.caption("10-Bagger Agent System v2 · 賽道與決策管理")
