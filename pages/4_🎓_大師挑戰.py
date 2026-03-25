"""
10-Bagger v2 — 大師挑戰頁 (Master Challenge)
Select investment masters, trigger n8n webhook, display debate results.
"""

import streamlit as st
import pandas as pd
import requests

from utils.supabase_client import (
    fetch_active_stocks,
    fetch_stock_probabilities,
    fetch_master_challenges,
)
from utils.constants import MASTERS

st.set_page_config(page_title="大師挑戰 | 10-Bagger", page_icon="🎓", layout="wide")
st.markdown("## 🎓 大師挑戰 (Investment Master Debate)")
st.caption("讓投資大師們針對你的持股進行辯論與驗證")

# ── Data ──────────────────────────────────────────────────────
stocks = fetch_active_stocks()
probs = fetch_stock_probabilities()
prob_map = {p["stock_ticker"]: p.get("current_ph", 0.15) for p in probs}

if not stocks:
    st.warning("尚無追蹤股票。")
    st.stop()

# ── Trigger section ───────────────────────────────────────────
st.markdown("### 🎯 發起大師挑戰")

col_form, col_masters = st.columns([1, 2])

with col_form:
    tickers = [s["ticker"] for s in stocks]
    challenge_ticker = st.selectbox("選擇股票", tickers, key="mc_ticker")

    current_ph = prob_map.get(challenge_ticker, 0.15)
    st.markdown(f"**目前 P(H):** {current_ph:.1%}")

    scope = st.radio(
        "挑戰範圍",
        ["full_review", "bull_case_only", "bear_case_only", "risk_assessment"],
        format_func=lambda x: {
            "full_review": "🔄 完整審查",
            "bull_case_only": "📈 僅 Bull Case",
            "bear_case_only": "📉 僅 Bear Case",
            "risk_assessment": "⚠️ 風險評估",
        }.get(x, x),
    )

with col_masters:
    st.markdown("**選擇參與大師**")

    master_cols = st.columns(3)
    selected_masters = []
    for idx, (key, info) in enumerate(MASTERS.items()):
        with master_cols[idx % 3]:
            if st.checkbox(
                f"{info['icon']} {info['name']}",
                value=True,
                key=f"master_{key}",
                help=f"{info['en']} — {info['philosophy']}",
            ):
                selected_masters.append(key)

    if selected_masters:
        st.markdown(
            "**已選：** "
            + " ".join(f"{MASTERS[m]['icon']}{MASTERS[m]['name']}" for m in selected_masters)
        )

st.markdown("---")

# Trigger button
if st.button("🚀 發起大師挑戰", use_container_width=True, type="primary"):
    if not selected_masters:
        st.error("請至少選擇一位大師。")
    else:
        webhook_base = st.secrets.get("n8n", {}).get("webhook_base", "")
        if not webhook_base:
            st.error("未設定 n8n webhook_base，請在 secrets.toml 中設定。")
        else:
            payload = {
                "stock_ticker": challenge_ticker,
                "scope": scope,
                "masters": selected_masters,
                "current_ph": current_ph,
                "triggered_by": "dashboard",
            }
            with st.spinner("正在觸發大師挑戰..."):
                try:
                    resp = requests.post(
                        f"{webhook_base}/master-challenge",
                        json=payload,
                        timeout=30,
                    )
                    if resp.status_code == 200:
                        st.success("大師挑戰已觸發！結果將在下方歷史記錄中顯示。")
                        result = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                        if result:
                            st.json(result)
                    else:
                        st.warning(f"觸發回應：HTTP {resp.status_code}")
                except requests.exceptions.Timeout:
                    st.info("請求已送出（非同步處理中）。結果完成後會出現在歷史記錄中。")
                except Exception as e:
                    st.error(f"觸發失敗：{e}")

st.divider()

# ── Challenge results / history ───────────────────────────────
st.markdown("### 📜 大師挑戰歷史")

challenges = fetch_master_challenges(limit=20)

if challenges:
    for ch in challenges:
        ticker = ch.get("stock_ticker", "—")
        created = ch.get("created_at", "")[:16]
        masters_used = ch.get("masters", [])
        if isinstance(masters_used, str):
            import json
            try:
                masters_used = json.loads(masters_used)
            except Exception:
                masters_used = [masters_used]

        master_icons = " ".join(
            MASTERS.get(m, {}).get("icon", "❓") for m in masters_used
        )

        with st.expander(f"🎓 {created} — {ticker} {master_icons}"):
            ch_scope = ch.get("scope", "full_review")
            st.markdown(f"**範圍：** {ch_scope} · **股票：** {ticker}")

            # Per-master results
            results = ch.get("results", {})
            if isinstance(results, str):
                import json
                try:
                    results = json.loads(results)
                except Exception:
                    results = {}

            if results:
                for master_key, verdict in results.items():
                    info = MASTERS.get(master_key, {"icon": "❓", "name": master_key})
                    st.markdown(f"#### {info['icon']} {info['name']}")

                    if isinstance(verdict, dict):
                        st.markdown(f"**結論：** {verdict.get('conclusion', '—')}")
                        st.markdown(f"**信心度：** {verdict.get('confidence', '—')}")

                        # Verification questions
                        questions = verdict.get("verification_questions", [])
                        if questions:
                            st.markdown("**驗證問題：**")
                            for qi, q in enumerate(questions[:3]):
                                st.markdown(f"{qi+1}. {q}")
                    else:
                        st.markdown(str(verdict)[:500])
            else:
                raw = ch.get("raw_result", ch.get("result_text", ""))
                if raw:
                    st.markdown(str(raw)[:1000])
                else:
                    st.caption("無詳細結果。")

            # Action buttons
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("✅ 套用建議", key=f"apply_{ch.get('id', created)}"):
                    st.info("套用功能需搭配 n8n Workflow 實作。")
            with col_btn2:
                if st.button("🔄 重新挑戰", key=f"retry_{ch.get('id', created)}"):
                    st.info("請在上方重新發起挑戰。")

    # History table
    st.markdown("#### 📋 挑戰一覽表")
    df_ch = pd.DataFrame(challenges)
    display_cols = ["stock_ticker", "scope", "created_at"]
    available = [c for c in display_cols if c in df_ch.columns]
    if available:
        df_display = df_ch[available].copy()
        df_display.columns = ["股票", "範圍", "時間"][:len(available)]
        st.dataframe(df_display, use_container_width=True, hide_index=True)
else:
    st.info("尚無大師挑戰記錄。發起第一次挑戰吧！")

st.divider()

# ── Master profiles ───────────────────────────────────────────
st.markdown("### 🏛️ 投資大師介紹")

master_cols = st.columns(3)
for idx, (key, info) in enumerate(MASTERS.items()):
    with master_cols[idx % 3]:
        st.markdown(
            f"### {info['icon']} {info['name']}\n"
            f"**{info['en']}**\n\n"
            f"📌 {info['philosophy']}\n\n"
            f"{info['description']}"
        )
        st.markdown("---")
