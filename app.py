"""
10-Bagger 戰情儀表板 v3.1 — Streamlit Cloud Edition
Features:
- Live Supabase data (stocks, tracks, probability_log, audit_log, master_opinions, master_challenges)
- v7 6-dimension scoring with breakdown
- Bayesian probability tracking with source citations
- Audit reports (Spearman Rho, zombie count, signal)
- Master challenge opinions from NotebookLM with 彼得林區 as 6th master
- Enhanced Bayesian analysis tab with charts and leverage
- Knowledge base management (notebook_sources CRUD)
- Master challenge batch mode
- Decision mailbox (decisions table)
- P(H) gauge charts for probability visualization
- NotebookLM data sources management
- Yahoo Finance news integration
- One-click n8n Screener trigger
"""
import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import xml.etree.ElementTree as ET

# ============================================================================
# CONFIG — reads from st.secrets (set in Streamlit Cloud → Settings → Secrets)
# ============================================================================
SUPABASE_URL = st.secrets["supabase"]["url"]
SERVICE_KEY = st.secrets["supabase"]["key"]
WEBHOOK_BASE = st.secrets.get("n8n", {}).get("webhook_base", "https://shawnhuang.app.n8n.cloud/webhook")
SCREENER_WEBHOOK = f"{WEBHOOK_BASE}/screener-agent"
MASTER_ANALYSIS_WEBHOOK = f"{WEBHOOK_BASE}/master-analysis"
MASTER_CHALLENGE_WEBHOOK = f"{WEBHOOK_BASE}/master-challenge"

st.set_page_config(
    page_title="10-Bagger 戰情儀表板 v3.1",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# v7 SCORE WEIGHTS — 6 dimensions
# ============================================================================
SCORE_WEIGHTS_V7 = {
    "gross_margin":     {"label": "毛利率 GM",       "weight": 0.15, "desc": "毛利率越高代表定價能力與競爭優勢越強"},
    "revenue_growth":   {"label": "營收成長 Rev",     "weight": 0.20, "desc": "年營收成長率，反映業務擴張速度"},
    "market_cap_score": {"label": "市值甜蜜點 MCap",  "weight": 0.15, "desc": "市值落在爆發甜蜜區間(500M-5B)得分最高"},
    "consistency":      {"label": "多年一致性 Cons",   "weight": 0.15, "desc": "多年度毛利率與營收成長穩定性"},
    "relevance_score":  {"label": "賽道相關性 Track",  "weight": 0.20, "desc": "Claude AI 判斷與賽道主題的相關程度"},
    "momentum_score":   {"label": "動能評分 Mom",      "weight": 0.15, "desc": "52週位置(50%)+日漲幅(30%)+量比(20%)"},
}

# ============================================================================
# MASTER OPINIONS DATA (from NotebookLM queries)
# ============================================================================
MASTERS = {
    "巴菲特": {
        "emoji": "🎩",
        "notebook_id": "ddbad0c0-54fd-46aa-abb9-f2fe37ecd581",
        "philosophy": "能力圈、護城河、安全邊際、管理層品質、ROE。以合理價格買卓越公司，勝過以極佳價格買平庸公司。",
        "key_principles": [
            "能力圈：只投資能理解的企業",
            "經濟護城河：需持久競爭優勢",
            "安全邊際：買入價須顯著低於內在價值",
            "優秀管理層：誠實且理性分配資本",
            "穩健財務：高ROE、穩定現金流、低負債",
        ],
    },
    "查理蒙格": {
        "emoji": "🧠",
        "notebook_id": "ca08d942-ac0f-4618-8371-ef8fe11f22e3",
        "philosophy": "能力圈、護城河、反向思考、乘法為零效應。態度極度謹慎，對新興科技避而遠之。",
        "key_principles": [
            "反向思考：先問「這會如何讓我慘敗」",
            "乘法為零效應：任何關鍵環節失敗，整體歸零",
            "護城河 vs 創造性破壞：新興科技難建持久護城河",
        ],
    },
    "霍華馬克斯": {
        "emoji": "📐",
        "notebook_id": "501b59ab-aa22-4579-a02a-d87f13d18dec",
        "philosophy": "第二層思考、風險評估、市場週期、逆向投資。真正的風險是永久虧損的可能性。",
        "key_principles": [
            "風險 ≠ 波動性：真正的風險是永久虧損",
            "市場週期必然輪迴：過度樂觀後必有修正",
            "第二層思考：共識看好時問「已反映在價格中了嗎？」",
        ],
    },
    "彼得提爾": {
        "emoji": "🚀",
        "notebook_id": "278cbbf1-e4cd-41b4-8bc2-da9f4fb1095c",
        "philosophy": "從0到1的創新、壟斷思維、冪次法則。競爭是失敗者的遊戲。",
        "key_principles": [
            "從0到1：尋找創造全新事物的公司",
            "壟斷思維：最好的企業是某個利基市場的壟斷者",
            "冪次法則：少數公司創造絕大部分回報",
        ],
    },
    "科斯托蘭尼": {
        "emoji": "🎭",
        "notebook_id": "1a101582-8f24-45ec-b7da-930f37f95dda",
        "philosophy": "雞蛋理論、人心與資金、固執投資人vs猶豫投資人。投機是一門藝術。",
        "key_principles": [
            "雞蛋理論：從固執投資人手中到猶豫投資人手中",
            "資金寬鬆+樂觀=上漲",
            "在絕望中買入，在歡樂中賣出",
        ],
    },
    "彼得林區": {
        "emoji": "🛒",
        "notebook_id": "",
        "philosophy": "生活選股、PEG比率、合理成長股。從日常生活中發現投資機會。",
        "key_principles": [
            "生活選股：從日常消費中發現好公司",
            "PEG < 1：成長率應超過本益比",
            "分類思考：依成長型、轉機型等分類評估",
            "長期持有：找到好公司後長期持有",
        ],
    },
}

# ============================================================================
# DATA FETCHING
# ============================================================================
HEADERS = {"apikey": SERVICE_KEY, "Authorization": f"Bearer {SERVICE_KEY}"}


@st.cache_data(ttl=120)
def fetch_supabase(table, select="*", order=None, limit=None, filters=None):
    url = f"{SUPABASE_URL}/rest/v1/{table}?select={select}"
    if order:
        url += f"&order={order}"
    if limit:
        url += f"&limit={limit}"
    if filters:
        url += f"&{filters}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"Supabase 讀取失敗 ({table}): {e}")
        return []


def write_supabase(table, data):
    """INSERT a row into Supabase."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    try:
        resp = requests.post(
            url,
            json=data,
            headers={**HEADERS, "Content-Type": "application/json", "Prefer": "return=minimal"},
            timeout=15
        )
        return resp.status_code in (200, 201)
    except Exception as e:
        st.error(f"寫入失敗: {e}")
        return False


def delete_supabase(table, column, value):
    """DELETE rows from Supabase matching column=value."""
    url = f"{SUPABASE_URL}/rest/v1/{table}?{column}=eq.{value}"
    try:
        resp = requests.delete(url, headers=HEADERS, timeout=15)
        return resp.status_code in (200, 204)
    except Exception as e:
        st.error(f"刪除失敗: {e}")
        return False


def patch_supabase(table, column, value, data):
    """PATCH (update) rows in Supabase matching column=value."""
    url = f"{SUPABASE_URL}/rest/v1/{table}?{column}=eq.{value}"
    try:
        resp = requests.patch(
            url,
            json=data,
            headers={**HEADERS, "Content-Type": "application/json", "Prefer": "return=minimal"},
            timeout=15
        )
        return resp.status_code in (200, 204)
    except Exception as e:
        st.error(f"更新失敗: {e}")
        return False


def trigger_screener():
    try:
        resp = requests.post(
            SCREENER_WEBHOOK,
            json={"trigger": "manual", "timestamp": datetime.now().isoformat()},
            timeout=10,
        )
        return resp.status_code, resp.text[:200]
    except Exception as e:
        return 0, str(e)


def trigger_master_challenge(master_names=None):
    """Trigger master challenge webhook for all 6 masters or specified ones."""
    try:
        payload = {
            "trigger": "manual",
            "masters": master_names or list(MASTERS.keys()),
            "timestamp": datetime.now().isoformat(),
        }
        resp = requests.post(
            MASTER_CHALLENGE_WEBHOOK,
            json=payload,
            timeout=30,
        )
        return resp.status_code, resp.text[:200]
    except Exception as e:
        return 0, str(e)


def call_master_analysis(ticker, company_name, master_name, master_notebook_id):
    try:
        resp = requests.post(
            MASTER_ANALYSIS_WEBHOOK,
            json={
                "ticker": ticker,
                "company_name": company_name,
                "master_name": master_name,
                "master_notebook_id": master_notebook_id,
                "timestamp": datetime.now().isoformat(),
            },
            timeout=60,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("analysis", resp.text[:2000])
        return f"⚠️ 分析服務回傳 HTTP {resp.status_code}"
    except requests.Timeout:
        return "⚠️ 分析請求逾時（60秒），請稍後再試"
    except Exception as e:
        return f"⚠️ 無法連線分析服務: {e}"


@st.cache_data(ttl=600)
def fetch_yahoo_news(ticker, market="US"):
    yahoo_ticker = ticker
    if market == "TW" and ".TW" not in ticker:
        yahoo_ticker = f"{ticker}.TW"
    elif market == "HK" and ".HK" not in ticker:
        yahoo_ticker = f"{ticker}.HK"
    elif market == "JP" and ".T" not in ticker:
        yahoo_ticker = f"{ticker}.T"
    url = f"https://finance.yahoo.com/rss/headline?s={yahoo_ticker}"
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0 (compatible; 10BaggerBot/1.0)"})
        if resp.status_code != 200:
            return []
        root = ET.fromstring(resp.content)
        items = []
        for item in root.findall(".//item")[:8]:
            title = item.find("title")
            link = item.find("link")
            pub_date = item.find("pubDate")
            items.append({
                "title": title.text if title is not None else "",
                "link": link.text if link is not None else "",
                "date": pub_date.text[:16] if pub_date is not None else "",
            })
        return items
    except Exception:
        return []


# ============================================================================
# URL HELPERS
# ============================================================================
def make_yahoo_url(ticker, market):
    if not ticker:
        return ""
    if market == "TW" and ".TW" not in ticker:
        return f"https://finance.yahoo.com/quote/{ticker}.TW"
    if market == "HK" and ".HK" not in ticker:
        return f"https://finance.yahoo.com/quote/{ticker}.HK"
    if market == "JP" and ".T" not in ticker:
        return f"https://finance.yahoo.com/quote/{ticker}.T"
    return f"https://finance.yahoo.com/quote/{ticker}"


def make_alphaspread_url(ticker, market):
    if not ticker:
        return ""
    t = ticker.replace(".TW", "").replace(".HK", "").replace(".T", "").lower()
    if market == "TW":
        return f"https://www.alphaspread.com/security/twse/{t}/summary"
    if market == "JP":
        return f"https://www.alphaspread.com/security/tse/{t}/summary"
    if market == "HK":
        return f"https://www.alphaspread.com/security/hkex/{t}/summary"
    return f"https://www.alphaspread.com/security/nasdaq/{t}/summary"


def fmt_pct(val):
    if val is None or val == 0:
        return "-"
    return f"{val:.1f}%"


def fmt_cap(val):
    if not val:
        return "-"
    if val >= 1e9:
        return f"${val/1e9:.2f}B"
    return f"${val/1e6:.0f}M"


def score_color(val):
    if val >= 80:
        return "🟢"
    elif val >= 60:
        return "🔵"
    elif val >= 40:
        return "🟡"
    else:
        return "🔴"


# ============================================================================
# SIDEBAR
# ============================================================================
with st.sidebar:
    st.title("🔍 10-Bagger v3.1")
    st.markdown("---")

    st.subheader("端到端測試")
    if st.button("🚀 觸發 Screener Agent", use_container_width=True):
        with st.spinner("觸發中..."):
            code, body = trigger_screener()
        if code == 200:
            st.success(f"✅ 觸發成功 (HTTP {code})")
        else:
            st.warning(f"⚠️ HTTP {code}: {body}")

    if st.button("🎓 全大師挑戰", use_container_width=True):
        with st.spinner("啟動全大師挑戰..."):
            code, body = trigger_master_challenge()
        if code == 200:
            st.success(f"✅ 挑戰已啟動 (HTTP {code})")
        else:
            st.warning(f"⚠️ HTTP {code}: {body}")

    if st.button("🔄 重新整理資料", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.subheader("系統資訊")
    st.caption("v7 六維度計分")
    st.caption("Supabase 即時連線")
    st.caption("NotebookLM 知識庫整合")
    st.caption(f"更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    st.markdown("---")
    st.subheader("標籤頁說明")
    st.markdown("""
    📋 **選股追蹤** — 篩選結果列表、個股詳情、分析
    📈 **機率變化** — P(H) 追蹤、趨勢圖、辯論卡片
    🔍 **稽核報告** — Spearman Rho、殭屍股、信號
    🏆 **大師看法** — 6大師觀點、哲學基礎
    📰 **最新資訊** — 證據、賽道研究、決策信箱
    📚 **資料來源** — 知識來源概覽
    📖 **知識庫管理** — CRUD 知識來源、狀態管理
    🎓 **大師挑戰** — 批量挑戰結果、嚴重性評估
    """)

    st.markdown("---")
    st.subheader("Scheduled Tasks")
    st.markdown("""
    - 📅 **Mon 08:00** Track Research
    - 📅 **Mon 12:00** Stock Research
    - 📅 **Wed 08:00** Quant Auditor
    """)


# ============================================================================
# FETCH ALL DATA
# ============================================================================
stocks_raw = fetch_supabase("stocks", order="composite_score.desc")
tracks_raw = fetch_supabase("tracks", order="id.asc")
prob_log_raw = fetch_supabase("probability_log", order="created_at.desc", limit=200)
audit_raw = fetch_supabase("audit_log", order="audit_date.desc", limit=50)
master_opinions_raw = fetch_supabase("master_opinions", order="created_at.desc", limit=100)
master_challenges_raw = fetch_supabase("master_challenges", order="challenged_at.desc", limit=20)
evidence_raw = fetch_supabase("evidence_log", order="created_at.desc", limit=100)
notebook_sources_raw = fetch_supabase("notebook_sources", order="created_at.desc", limit=200)
decisions_raw = fetch_supabase("decisions", order="created_at.desc", limit=50)

# ============================================================================
# DATAFRAMES
# ============================================================================
df = pd.DataFrame(stocks_raw) if stocks_raw else pd.DataFrame()
df_tracks = pd.DataFrame(tracks_raw) if tracks_raw else pd.DataFrame()
df_prob = pd.DataFrame(prob_log_raw) if prob_log_raw else pd.DataFrame()
df_audit = pd.DataFrame(audit_raw) if audit_raw else pd.DataFrame()
df_masters = pd.DataFrame(master_opinions_raw) if master_opinions_raw else pd.DataFrame()
df_challenges = pd.DataFrame(master_challenges_raw) if master_challenges_raw else pd.DataFrame()
df_evidence = pd.DataFrame(evidence_raw) if evidence_raw else pd.DataFrame()
df_sources = pd.DataFrame(notebook_sources_raw) if notebook_sources_raw else pd.DataFrame()
df_decisions = pd.DataFrame(decisions_raw) if decisions_raw else pd.DataFrame()

# ============================================================================
# TITLE & METRICS
# ============================================================================
st.title("📊 10-Bagger 戰情儀表板 v3.1")

if df.empty:
    st.warning("⚠️ 尚無篩選結果。請點擊左側「觸發 Screener Agent」執行篩選。")
    st.stop()

# Ensure URL columns
if "yahoo_finance_url" not in df.columns:
    df["yahoo_finance_url"] = ""
if "alphaspread_url" not in df.columns:
    df["alphaspread_url"] = ""
for idx, row in df.iterrows():
    if not row.get("yahoo_finance_url"):
        df.at[idx, "yahoo_finance_url"] = make_yahoo_url(row.get("ticker", ""), row.get("market", ""))
    if not row.get("alphaspread_url"):
        df.at[idx, "alphaspread_url"] = make_alphaspread_url(row.get("ticker", ""), row.get("market", ""))

# KPI Row
col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1:
    st.metric("篩選股票", len(df))
with col2:
    st.metric("活躍賽道", len(df_tracks))
with col3:
    avg_score = df["composite_score"].mean() if "composite_score" in df.columns else 0
    st.metric("平均綜合分", f"{avg_score:.1f}")
with col4:
    st.metric("機率更新", len(df_prob))
with col5:
    st.metric("稽核報告", len(df_audit))
with col6:
    nlm_count = df["nlm_notebook_id"].notna().sum() if "nlm_notebook_id" in df.columns else 0
    st.metric("NLM 研究", nlm_count)

st.markdown("---")

# ============================================================================
# TABS (8 TABS)
# ============================================================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📋 選股追蹤", "📈 機率變化", "🔍 稽核報告",
    "🏆 大師看法", "📰 最新資訊", "📚 資料來源",
    "📖 知識庫管理", "🎓 大師挑戰",
])

# ============================================================================
# TAB 1: 選股追蹤 (Stock Tracking)
# ============================================================================
with tab1:
    st.subheader("篩選股票列表")

    # Track weights overview
    if not df_tracks.empty:
        tcol1, tcol2 = st.columns([1, 2])
        with tcol1:
            st.markdown("**賽道權重配置**")
            for _, t in df_tracks.iterrows():
                w = t.get("weight", 0)
                name = t.get("name", "")
                nlm = "✅" if t.get("nlm_notebook_id") else "❌"
                st.markdown(f"- **{name}** — {w}% {nlm}")
        with tcol2:
            if "weight" in df_tracks.columns:
                fig_track = px.pie(
                    df_tracks, values="weight", names="name",
                    title="賽道權重分配",
                    color_discrete_sequence=px.colors.qualitative.Set2,
                )
                fig_track.update_layout(template="plotly_dark", height=300)
                st.plotly_chart(fig_track, use_container_width=True)

    st.markdown("---")

    # Filters
    fcol1, fcol2, fcol3 = st.columns(3)
    with fcol1:
        market_opts = sorted(df["market"].unique()) if "market" in df.columns else []
        market_filter = st.multiselect("市場", options=market_opts, default=market_opts)
    with fcol2:
        if "track_name" in df.columns:
            track_opts = sorted(df["track_name"].dropna().unique())
            track_filter = st.multiselect("賽道", options=track_opts, default=track_opts)
        else:
            track_filter = []
    with fcol3:
        max_score = float(df["composite_score"].max()) if "composite_score" in df.columns else 100.0
        min_score = st.slider("最低綜合分", 0.0, max_score, 0.0)

    filtered = df.copy()
    if market_filter and "market" in filtered.columns:
        filtered = filtered[filtered["market"].isin(market_filter)]
    if track_filter and "track_name" in filtered.columns:
        filtered = filtered[filtered["track_name"].isin(track_filter)]
    if "composite_score" in filtered.columns:
        filtered = filtered[filtered["composite_score"] >= min_score]

    st.caption(f"顯示 {len(filtered)} / {len(df)} 檔股票")

    # Table
    display_cols = []
    for _, row in filtered.iterrows():
        sc = row.get("composite_score", 0) or 0
        display_cols.append({
            "": score_color(sc),
            "Ticker": row.get("ticker", ""),
            "公司名稱": row.get("name", ""),
            "市場": row.get("market", ""),
            "賽道": row.get("track_name", "-"),
            "市值": fmt_cap(row.get("market_cap")),
            "毛利率": fmt_pct(row.get("gross_margin")),
            "營收成長": fmt_pct(row.get("revenue_growth")),
            "綜合分": f"{sc:.1f}",
            "P(H)": f"{row.get('current_ph', 0):.1%}" if row.get("current_ph") else "-",
            "NLM": "✅" if row.get("nlm_notebook_id") else "",
            "Yahoo": row.get("yahoo_finance_url", ""),
            "Alphaspread": row.get("alphaspread_url", ""),
        })

    display_df = pd.DataFrame(display_cols)
    st.dataframe(
        display_df,
        column_config={
            "Yahoo": st.column_config.LinkColumn("Yahoo", display_text="📈"),
            "Alphaspread": st.column_config.LinkColumn("Alphaspread", display_text="📊"),
        },
        hide_index=True, use_container_width=True, height=500,
    )

    # ---- STOCK DETAIL PANEL ----
    st.markdown("---")
    st.subheader("🔍 個股詳細分析")

    ticker_options = filtered["ticker"].tolist() if not filtered.empty else []
    if ticker_options:
        selected_ticker = st.selectbox(
            "選擇股票查看詳情",
            options=["-- 請選擇 --"] + ticker_options,
            index=0, key="stock_detail_select",
        )

        if selected_ticker != "-- 請選擇 --":
            stock_row = filtered[filtered["ticker"] == selected_ticker].iloc[0]
            stock_name = stock_row.get("name", selected_ticker)
            stock_market = stock_row.get("market", "US")

            st.markdown(f"### {selected_ticker} — {stock_name}")

            detail_tab1, detail_tab2, detail_tab3, detail_tab4 = st.tabs(
                ["📊 v7 分數計算", "🏆 大師即時分析", "📈 機率規儀", "📰 近期新聞"]
            )

            with detail_tab1:
                composite = stock_row.get("composite_score", 0) or 0
                st.metric("綜合分數", f"{composite:.1f} / 100")

                # Score breakdown from JSONB if available
                breakdown = stock_row.get("score_breakdown")
                if breakdown and isinstance(breakdown, dict):
                    st.markdown("**v7 六維度分數明細：**")
                    bd_data = []
                    for key, info in SCORE_WEIGHTS_V7.items():
                        val = breakdown.get(key, breakdown.get(info["label"], 0))
                        if val is None:
                            val = 0
                        bd_data.append({
                            "維度": info["label"],
                            "原始分": round(float(val), 1),
                            "權重": f"{info['weight']:.0%}",
                            "加權貢獻": round(float(val) * info["weight"], 1),
                        })
                    bd_df = pd.DataFrame(bd_data)
                    st.dataframe(bd_df, hide_index=True, use_container_width=True)

                    fig_bd = px.bar(
                        bd_df, x="維度", y="加權貢獻",
                        title=f"{selected_ticker} v7 六維度加權貢獻",
                        color="加權貢獻", color_continuous_scale="Viridis",
                    )
                    fig_bd.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig_bd, use_container_width=True)
                else:
                    st.markdown("**各維度原始值：**")
                    for key, info in SCORE_WEIGHTS_V7.items():
                        raw_val = stock_row.get(key)
                        st.markdown(f"- **{info['label']}** (權重 {info['weight']:.0%}): {fmt_pct(raw_val) if raw_val else '-'}")

                reasoning = stock_row.get("reasoning", "")
                if reasoning:
                    st.markdown("#### 🤖 AI 篩選理由")
                    st.info(reasoning)

                st.markdown("#### 🔗 研究連結")
                lcol1, lcol2, lcol3 = st.columns(3)
                with lcol1:
                    st.markdown(f"[📈 Yahoo Finance]({make_yahoo_url(selected_ticker, stock_market)})")
                with lcol2:
                    st.markdown(f"[📊 Alphaspread]({make_alphaspread_url(selected_ticker, stock_market)})")
                with lcol3:
                    st.markdown(f"[🔍 Google News](https://news.google.com/search?q={selected_ticker}%20stock)")

            with detail_tab2:
                st.markdown("#### 選擇投資大師進行即時分析")
                master_names = list(MASTERS.keys())
                selected_master = st.selectbox("選擇大師", master_names, key=f"master_{selected_ticker}")
                master_info = MASTERS[selected_master]

                with st.expander(f"{master_info['emoji']} {selected_master} 的投資哲學"):
                    for p in master_info["key_principles"]:
                        st.markdown(f"- {p}")

                # Show existing opinions from DB
                if not df_masters.empty and "stock_ticker" in df_masters.columns:
                    existing = df_masters[
                        (df_masters["stock_ticker"] == selected_ticker) &
                        (df_masters["master_name"] == selected_master)
                    ]
                    if not existing.empty:
                        st.markdown(f"**📝 已有 {len(existing)} 筆歷史觀點：**")
                        for _, op in existing.iterrows():
                            st.markdown(f"- **{op.get('question', '')}**")
                            st.markdown(f"  > {op.get('opinion', '')}")
                            sev = op.get("severity", "")
                            if sev:
                                st.caption(f"嚴重性: {sev}")

                cache_key = f"analysis_{selected_ticker}_{selected_master}"
                if st.button(f"🔮 以{selected_master}視角分析 {selected_ticker}", use_container_width=True):
                    with st.spinner(f"正在以{selected_master}的視角分析 {stock_name}..."):
                        analysis = call_master_analysis(
                            selected_ticker, stock_name,
                            selected_master, master_info["notebook_id"],
                        )
                        st.session_state[cache_key] = analysis

                if cache_key in st.session_state:
                    st.markdown(f"### {master_info['emoji']} {selected_master}對 {selected_ticker} 的看法")
                    st.markdown(st.session_state[cache_key])

            with detail_tab3:
                st.markdown(f"#### 📈 {selected_ticker} P(H) 十倍股機率")
                current_ph = stock_row.get("current_ph", 0.5) or 0.5

                # Gauge chart
                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=current_ph * 100,
                    title={"text": "P(H) 十倍股機率"},
                    gauge={
                        "axis": {"range": [0, 100]},
                        "bar": {"color": "#38bdf8"},
                        "steps": [
                            {"range": [0, 30], "color": "#ef4444"},
                            {"range": [30, 70], "color": "#f59e0b"},
                            {"range": [70, 100], "color": "#22c55e"},
                        ],
                        "threshold": {"line": {"color": "white", "width": 2}, "value": 50},
                    },
                ))
                fig_gauge.update_layout(template="plotly_dark", height=250)
                st.plotly_chart(fig_gauge, use_container_width=True)

            with detail_tab4:
                st.markdown(f"#### 📰 {selected_ticker} 近期新聞")
                with st.spinner("載入新聞中..."):
                    news = fetch_yahoo_news(selected_ticker, stock_market)
                if news:
                    for item in news:
                        st.markdown(f"- [{item['title']}]({item['link']}) *({item['date']})*")
                else:
                    st.info(f"暫無 {selected_ticker} 的 Yahoo Finance 新聞。")
                st.markdown(f"[🔍 Google News 搜尋](https://news.google.com/search?q={selected_ticker}%20stock)")

# ============================================================================
# TAB 2: 機率變化 (Probability Changes) — ENHANCED
# ============================================================================
with tab2:
    st.subheader("📈 貝葉斯機率更新追蹤")

    if df_prob.empty:
        st.info("尚無貝葉斯更新記錄。排程任務 `quant-auditor` 將於每週三 08:00 自動執行。")
    else:
        st.markdown(f"共 **{len(df_prob)}** 筆更新，涵蓋 **{df_prob['stock_ticker'].nunique()}** 檔股票")

        pcol1, pcol2, pcol3, pcol4 = st.columns(4)
        with pcol1:
            surges = len(df_prob[df_prob["alert_type"] == "surge"]) if "alert_type" in df_prob.columns else 0
            st.metric("🚀 機率飆升", surges)
        with pcol2:
            dangers = len(df_prob[df_prob["alert_type"] == "danger"]) if "alert_type" in df_prob.columns else 0
            st.metric("⚠️ 風險警告", dangers)
        with pcol3:
            avg_conf = df_prob["confidence"].mean() if "confidence" in df_prob.columns else 0
            st.metric("平均信心度", f"{avg_conf:.0%}" if avg_conf else "-")
        with pcol4:
            avg_change = df_prob["change_amount"].mean() if "change_amount" in df_prob.columns else 0
            st.metric("平均變動", f"{avg_change:+.4f}" if avg_change else "-")

        st.markdown("---")

        # ---- ENHANCED: 全股 P(H) 橫條圖 ----
        if "current_ph" in df.columns:
            st.markdown("#### 全股 P(H) 比較")
            df_ph_chart = df[["ticker", "current_ph"]].copy()
            df_ph_chart = df_ph_chart.dropna(subset=["current_ph"])
            if not df_ph_chart.empty:
                df_ph_chart = df_ph_chart.sort_values("current_ph", ascending=True).tail(20)
                fig_ph = px.barh(
                    df_ph_chart, x="current_ph", y="ticker",
                    title="全股 P(H) 十倍股機率 Top 20",
                    labels={"current_ph": "P(H)", "ticker": "代號"},
                    color="current_ph", color_continuous_scale="RdYlGn"
                )
                fig_ph.update_layout(template="plotly_dark", height=400)
                st.plotly_chart(fig_ph, use_container_width=True)

        st.markdown("---")

        # ---- ENHANCED: P(H) 趨勢折線圖 ----
        st.markdown("#### P(H) 趨勢分析")
        if not df_prob.empty and "stock_ticker" in df_prob.columns:
            ticker_opts_prob = sorted(df_prob["stock_ticker"].unique())
            selected_ticker_prob = st.selectbox("選擇股票查看 P(H) 趨勢", ticker_opts_prob, key="prob_ticker")

            df_ticker_prob = df_prob[df_prob["stock_ticker"] == selected_ticker_prob].copy()
            if not df_ticker_prob.empty:
                df_ticker_prob = df_ticker_prob.sort_values("created_at")

                fig_trend = go.Figure()
                fig_trend.add_trace(go.Scatter(
                    x=df_ticker_prob["created_at"],
                    y=df_ticker_prob["new_ph"],
                    mode="lines+markers",
                    name="P(H)",
                    line=dict(color="#38bdf8", width=2),
                    marker=dict(size=6),
                ))
                if "prior_ph" in df_ticker_prob.columns:
                    fig_trend.add_trace(go.Scatter(
                        x=df_ticker_prob["created_at"],
                        y=df_ticker_prob["prior_ph"],
                        mode="lines",
                        name="Prior P(H)",
                        line=dict(color="#94a3b8", width=1, dash="dash"),
                    ))

                fig_trend.update_layout(
                    title=f"{selected_ticker_prob} P(H) 趨勢",
                    xaxis_title="日期", yaxis_title="P(H)",
                    template="plotly_dark", height=350,
                )
                st.plotly_chart(fig_trend, use_container_width=True)

        st.markdown("---")

        # ---- BULL/BEAR/JUDGE 辯論卡片 ----
        st.markdown("#### 機率更新辯論卡片")
        for _, row in df_prob.iterrows():
            ticker = row.get("stock_ticker", "")
            prior = row.get("prior_ph", 0) or 0
            new_ph = row.get("new_ph", 0) or 0
            change = row.get("change_amount", 0) or 0
            confidence = row.get("confidence", 0) or 0
            alert = row.get("alert_type", "")
            bull = row.get("bull_reasoning", "")
            bear = row.get("bear_counter_argument", "")
            judge = row.get("judge_ruling", "")
            evidence_count = row.get("evidence_count", 0) or 0
            created_at = row.get("created_at", "")
            source_refs = row.get("source_references", [])
            lr = row.get("likelihood_ratio")
            evidence_summary = row.get("evidence_summary", "")
            trigger = row.get("trigger_source", "")

            icon = "🟢" if change > 0.1 else ("🔴" if change < -0.05 else "🟡")
            alert_badge = "🚀 SURGE" if alert == "surge" else ("⚠️ DANGER" if alert == "danger" else "")

            with st.container(border=True):
                hcol1, hcol2, hcol3, hcol4, hcol5 = st.columns([2, 1, 1, 1, 1])
                with hcol1:
                    st.markdown(f"### {icon} {ticker} {alert_badge}")
                with hcol2:
                    st.metric("Prior P(H)", f"{prior:.1%}")
                with hcol3:
                    st.metric("New P(H)", f"{new_ph:.1%}", delta=f"{change:+.4f}")
                with hcol4:
                    st.metric("信心度", f"{confidence:.0%}")
                with hcol5:
                    if lr:
                        st.metric("Likelihood Ratio", f"{lr:.2f}")

                if evidence_summary:
                    st.markdown(f"**📝 證據摘要：** {evidence_summary}")

                if bull or bear or judge:
                    direction = "上升" if change > 0 else "下降" if change < 0 else "持平"
                    rcol1, rcol2 = st.columns(2)
                    with rcol1:
                        if bull:
                            st.markdown(f"**🐂 多方論點：** {bull}")
                    with rcol2:
                        if bear:
                            st.markdown(f"**🐻 空方反駁：** {bear}")
                    if judge:
                        st.markdown(f"**⚖️ 裁判裁決：** {judge}")

                # Source references
                if source_refs and isinstance(source_refs, list) and len(source_refs) > 0:
                    st.markdown("**📚 資料來源：**")
                    for ref in source_refs:
                        ref_url = ref.get("url", "")
                        ref_desc = ref.get("description", ref.get("type", ""))
                        if ref_url:
                            st.markdown(f"- [{ref_desc}]({ref_url})")
                        else:
                            st.markdown(f"- {ref_desc}")

                meta = []
                if trigger:
                    meta.append(f"觸發: {trigger}")
                if evidence_count:
                    meta.append(f"證據數: {evidence_count}")
                if created_at:
                    meta.append(f"時間: {str(created_at)[:19].replace('T', ' ')}")
                if meta:
                    st.caption(" | ".join(meta))

# ============================================================================
# TAB 3: 稽核報告 (Audit Reports)
# ============================================================================
with tab3:
    st.subheader("🔍 稽核報告")

    if df_audit.empty:
        st.info("尚無稽核報告。排程任務 `quant-auditor` 將於每週三自動生成。")
    else:
        st.markdown(f"共 **{len(df_audit)}** 筆稽核記錄")

        # Spearman Rho trend chart
        if "spearman_rho" in df_audit.columns:
            df_audit_sorted = df_audit.sort_values("audit_date")
            fig_rho = go.Figure()
            fig_rho.add_trace(go.Scatter(
                x=df_audit_sorted["audit_date"],
                y=df_audit_sorted["spearman_rho"],
                mode="lines+markers",
                name="Spearman Rho",
                line=dict(color="#38bdf8", width=2),
                marker=dict(size=8),
            ))
            fig_rho.add_hline(y=0.85, line_dash="dash", line_color="green", annotation_text="良好 (0.85)")
            fig_rho.add_hline(y=0.75, line_dash="dash", line_color="orange", annotation_text="警告 (0.75)")
            fig_rho.update_layout(
                title="Spearman Rho 趨勢（排序一致性）",
                xaxis_title="日期", yaxis_title="Spearman ρ",
                template="plotly_dark", height=350,
            )
            st.plotly_chart(fig_rho, use_container_width=True)

        # Audit table
        audit_display = []
        for _, row in df_audit.iterrows():
            signal = row.get("signal", "")
            signal_icon = "🟢" if signal == "green" else ("🟡" if signal == "yellow" else "🔴")
            audit_display.append({
                "信號": signal_icon,
                "日期": str(row.get("audit_date", ""))[:10],
                "類型": row.get("audit_type", ""),
                "Spearman ρ": f"{row.get('spearman_rho', 0):.3f}" if row.get("spearman_rho") else "-",
                "殭屍股數": row.get("zombie_count", 0),
            })
        st.dataframe(pd.DataFrame(audit_display), hide_index=True, use_container_width=True)

        # Detailed report for most recent
        if not df_audit.empty:
            latest = df_audit.iloc[0]
            report_json = latest.get("report_json")
            if report_json and isinstance(report_json, dict):
                st.markdown("#### 最新稽核報告詳情")
                st.json(report_json)

# ============================================================================
# TAB 4: 大師看法 (Master Opinions)
# ============================================================================
with tab4:
    st.subheader("🏆 投資大師看法")

    # Show master challenges summary
    if not df_challenges.empty:
        st.markdown(f"**已完成 {len(df_challenges)} 次大師挑戰**")
        for _, ch in df_challenges.iterrows():
            master_zh = ch.get("master_name_zh", ch.get("master_style", ""))
            q_count = ch.get("questions_count", 0)
            severity = ch.get("max_severity", "")
            date = str(ch.get("challenged_at", ""))[:10]
            st.markdown(f"- **{master_zh}** — {q_count} 題，最高嚴重性: {severity}，日期: {date}")
        st.markdown("---")

    # Show individual master opinions from DB
    if not df_masters.empty:
        st.markdown(f"**共 {len(df_masters)} 筆大師觀點記錄**")

        # Group by master
        if "master_name" in df_masters.columns:
            master_groups = df_masters.groupby("master_name")
            for master_name, group in master_groups:
                master_info = MASTERS.get(master_name, {})
                emoji = master_info.get("emoji", "🎯")

                with st.expander(f"{emoji} {master_name} ({len(group)} 筆觀點)", expanded=True):
                    if "philosophy" in master_info:
                        st.caption(master_info["philosophy"])

                    for _, op in group.iterrows():
                        ticker = op.get("stock_ticker", "")
                        scope = op.get("scope", "")
                        question = op.get("question", "")
                        opinion = op.get("opinion", "")
                        severity = op.get("severity", "")
                        philosophy = op.get("philosophy_base", "")

                        sev_color = "🔴" if severity == "high" else ("🟡" if severity == "medium" else "🟢")

                        st.markdown(f"**{sev_color} [{ticker}] {question}**")
                        st.markdown(f"> {opinion}")
                        if philosophy:
                            st.caption(f"哲學基礎: {philosophy} | 範圍: {scope}")
                        st.markdown("---")
    else:
        # Show static master philosophies
        st.markdown("尚無 DB 中的大師觀點。以下是各大師投資哲學概覽：")
        for master_name, master in MASTERS.items():
            with st.expander(f"{master['emoji']} {master_name}", expanded=False):
                st.markdown(f"**{master['philosophy']}**")
                for p in master["key_principles"]:
                    st.markdown(f"- {p}")

    st.markdown("---")
    st.info("💡 在「選股追蹤」分頁選擇個股 → 「大師即時分析」可觸發即時 NotebookLM 分析。")

# ============================================================================
# TAB 5: 最新資訊 (Latest Info) — ENHANCED
# ============================================================================
with tab5:
    st.subheader("📰 最新系統活動")

    # Recent evidence
    if not df_evidence.empty:
        st.markdown(f"#### 最新證據記錄 ({len(df_evidence)} 筆)")
        for _, ev in df_evidence.head(15).iterrows():
            ticker = ev.get("stock_ticker", "")
            summary = ev.get("key_evidence_summary", "")
            conf = ev.get("confidence_level", "")
            source = ev.get("source_type", "")
            date = str(ev.get("created_at", ""))[:19].replace("T", " ")

            conf_icon = "🟢" if conf == "high" else ("🟡" if conf == "medium" else "🔴")

            with st.container(border=True):
                ecol1, ecol2 = st.columns([3, 1])
                with ecol1:
                    st.markdown(f"**{ticker}** — {summary[:200] if summary else '無摘要'}")
                    st.caption(f"來源: {source} | 信心: {conf_icon} {conf} | {date}")
                with ecol2:
                    ev_count = ev.get("evidence_count", 0)
                    st.metric("證據數", ev_count)
    else:
        st.info("尚無證據記錄。")

    st.markdown("---")

    # Track research summaries
    if not df_tracks.empty:
        st.markdown("#### 賽道研究摘要")
        for _, t in df_tracks.iterrows():
            name = t.get("name", "")
            summary = t.get("research_summary", "")
            nlm_id = t.get("nlm_notebook_id", "")
            weight = t.get("weight", 0)

            with st.expander(f"🔷 {name} (權重 {weight}%)", expanded=False):
                if summary:
                    st.markdown(summary)
                else:
                    st.info("尚無研究摘要")
                if nlm_id:
                    st.caption(f"NotebookLM ID: {nlm_id}")

                # Show catalysts and risks if available
                catalysts = t.get("key_catalysts")
                risks = t.get("risks")
                if catalysts:
                    st.markdown("**關鍵催化劑：**")
                    if isinstance(catalysts, list):
                        for c in catalysts:
                            st.markdown(f"- {c}")
                    else:
                        st.json(catalysts)
                if risks:
                    st.markdown("**風險因素：**")
                    if isinstance(risks, list):
                        for r in risks:
                            st.markdown(f"- {r}")
                    else:
                        st.json(risks)

    st.markdown("---")

    # ---- ENHANCED: 決策信箱 ----
    st.markdown("#### 📬 決策信箱")
    if not df_decisions.empty:
        st.markdown(f"**共 {len(df_decisions)} 筆決策記錄**")
        for _, dec in df_decisions.iterrows():
            ticker = dec.get("stock_ticker", "")
            action = dec.get("action", "")
            reasoning = dec.get("reasoning", "")
            status = dec.get("status", "pending")
            decision_id = dec.get("id", "")

            status_icon = "✅" if status == "approved" else ("❌" if status == "rejected" else "⏳")

            with st.container(border=True):
                dcol1, dcol2, dcol3 = st.columns([2, 2, 1])
                with dcol1:
                    st.markdown(f"**{status_icon} [{ticker}] {action.upper()}**")
                    st.markdown(f"> {reasoning}")
                with dcol2:
                    st.caption(f"狀態: {status}")
                    st.caption(f"日期: {str(dec.get('created_at', ''))[:10]}")
                with dcol3:
                    if status == "pending":
                        if st.button("✅ 批准", key=f"approve_{decision_id}"):
                            if patch_supabase("decisions", "id", str(decision_id), {"status": "approved"}):
                                st.success("已批准")
                                st.cache_data.clear()
                                st.rerun()
                        if st.button("❌ 拒絕", key=f"reject_{decision_id}"):
                            if patch_supabase("decisions", "id", str(decision_id), {"status": "rejected"}):
                                st.success("已拒絕")
                                st.cache_data.clear()
                                st.rerun()
    else:
        st.info("尚無決策記錄。")

# ============================================================================
# TAB 6: 資料來源 (Data Sources)
# ============================================================================
with tab6:
    st.subheader("📚 NotebookLM 資料來源管理")

    # Summary
    scol1, scol2, scol3, scol4 = st.columns(4)
    with scol1:
        st.metric("總來源數", len(df_sources))
    with scol2:
        track_nlm = df_tracks["nlm_notebook_id"].notna().sum() if not df_tracks.empty and "nlm_notebook_id" in df_tracks.columns else 0
        st.metric("賽道 NLM", track_nlm)
    with scol3:
        stock_nlm = df["nlm_notebook_id"].notna().sum() if "nlm_notebook_id" in df.columns else 0
        st.metric("個股 NLM", stock_nlm)
    with scol4:
        active_sources = len(df_sources[df_sources["status"] == "active"]) if not df_sources.empty and "status" in df_sources.columns else len(df_sources)
        st.metric("活躍來源", active_sources)

    st.markdown("---")

    # Track notebooks
    st.markdown("#### 賽道 NotebookLM")
    if not df_tracks.empty:
        for _, t in df_tracks.iterrows():
            nlm_id = t.get("nlm_notebook_id", "")
            name = t.get("name", "")
            if nlm_id:
                st.markdown(f"- ✅ **{name}** — `{nlm_id}`")
            else:
                st.markdown(f"- ❌ **{name}** — 尚無 NotebookLM")

    st.markdown("---")

    # Stock notebooks
    st.markdown("#### 個股 NotebookLM")
    if not df.empty and "nlm_notebook_id" in df.columns:
        stocks_with_nlm = df[df["nlm_notebook_id"].notna()]
        stocks_without_nlm = df[df["nlm_notebook_id"].isna()]

        if not stocks_with_nlm.empty:
            for _, s in stocks_with_nlm.iterrows():
                st.markdown(f"- ✅ **{s['ticker']}** ({s.get('name', '')}) — `{s['nlm_notebook_id']}`")

        if not stocks_without_nlm.empty:
            st.caption(f"另有 {len(stocks_without_nlm)} 檔股票尚無 NotebookLM 深度研究")

    st.markdown("---")

    # Notebook sources table
    if not df_sources.empty:
        st.markdown("#### 所有知識來源")

        # Group by ticker
        if "ticker" in df_sources.columns:
            source_groups = df_sources.groupby("ticker")
            for ticker, group in source_groups:
                with st.expander(f"📌 {ticker} ({len(group)} 筆來源)"):
                    src_display = []
                    for _, s in group.iterrows():
                        src_display.append({
                            "標題": s.get("title", s.get("file_name", "")),
                            "類型": s.get("source_type", ""),
                            "來源": s.get("source_org", ""),
                            "狀態": s.get("status", ""),
                            "新增者": s.get("added_by", ""),
                            "日期": str(s.get("created_at", ""))[:10],
                        })
                    st.dataframe(pd.DataFrame(src_display), hide_index=True, use_container_width=True)
    else:
        st.info("尚無 notebook_sources 記錄。")

# ============================================================================
# TAB 7: 知識庫管理 (Knowledge Base Management) — NEW
# ============================================================================
with tab7:
    st.subheader("📖 知識庫管理")

    st.markdown("#### 新增知識來源")

    with st.form("add_source_form", border=False):
        form_col1, form_col2 = st.columns(2)

        with form_col1:
            source_ticker = st.text_input("股票代號 (Ticker)", placeholder="e.g., AAPL")
            source_title = st.text_input("來源標題", placeholder="e.g., 蘋果 2024 Q4 財報")
            source_type = st.selectbox("來源類型", ["earnings_report", "news", "research", "competitor", "industry", "other"])

        with form_col2:
            source_org = st.text_input("來源機構", placeholder="e.g., Bloomberg, Reuters")
            source_url = st.text_input("URL (可選)", placeholder="https://...")
            source_status = st.selectbox("狀態", ["active", "archived", "pending"])

        submitted = st.form_submit_button("➕ 新增", use_container_width=True)

        if submitted:
            if source_ticker and source_title and source_type:
                new_source = {
                    "ticker": source_ticker.upper(),
                    "title": source_title,
                    "source_type": source_type,
                    "source_org": source_org,
                    "url": source_url if source_url else None,
                    "status": source_status,
                    "added_by": "dashboard",
                    "created_at": datetime.now().isoformat(),
                }
                if write_supabase("notebook_sources", new_source):
                    st.success(f"✅ 已新增 {source_title}")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("新增失敗，請重試")
            else:
                st.warning("請填寫必填欄位：股票代號、標題、來源類型")

    st.markdown("---")
    st.markdown("#### 管理知識來源")

    if not df_sources.empty:
        # Show sources with delete buttons
        if "ticker" in df_sources.columns:
            source_groups = df_sources.groupby("ticker")
            for ticker, group in source_groups:
                with st.expander(f"🔧 {ticker} ({len(group)} 筆來源)", expanded=False):
                    for idx, (_, s) in enumerate(group.iterrows()):
                        scol1, scol2, scol3 = st.columns([3, 1, 1])
                        with scol1:
                            st.markdown(f"**{s.get('title', '')}**")
                            st.caption(f"{s.get('source_type', '')} | {s.get('source_org', '')} | {s.get('status', '')}")
                            if s.get('url'):
                                st.caption(f"[🔗 連結]({s.get('url')})")
                        with scol2:
                            st.caption(f"{str(s.get('created_at', ''))[:10]}")
                        with scol3:
                            source_id = s.get('id', '')
                            if source_id and st.button("🗑️", key=f"del_src_{source_id}"):
                                if delete_supabase("notebook_sources", "id", str(source_id)):
                                    st.success("已刪除")
                                    st.cache_data.clear()
                                    st.rerun()
                                else:
                                    st.error("刪除失敗")
    else:
        st.info("尚無知識來源。請上方新增。")

# ============================================================================
# TAB 8: 大師挑戰 (Master Challenge) — NEW
# ============================================================================
with tab8:
    st.subheader("🎓 大師挑戰")

    st.markdown("#### 啟動大師挑戰")

    mcol1, mcol2 = st.columns([2, 1])
    with mcol1:
        st.markdown("**觸發全部 6 位大師對篩選股票的集體挑戰**")
        st.caption("系統將針對每檔股票詢問所有大師各自的投資觀點，評估相容性與風險。")

    with mcol2:
        if st.button("🎓 啟動全大師挑戰", use_container_width=True):
            with st.spinner("啟動中..."):
                code, body = trigger_master_challenge()
            if code == 200:
                st.success(f"✅ 挑戰已啟動 (HTTP {code})")
            else:
                st.warning(f"⚠️ HTTP {code}: {body}")

    st.markdown("---")

    # Show master challenges summary and details
    if not df_challenges.empty:
        st.markdown(f"#### 挑戰結果 (共 {len(df_challenges)} 次挑戰)")

        for _, ch in df_challenges.iterrows():
            challenge_id = ch.get("id", "")
            master_zh = ch.get("master_name_zh", ch.get("master_style", ""))
            q_count = ch.get("questions_count", 0)
            severity = ch.get("max_severity", "")
            date = str(ch.get("challenged_at", ""))[:10]

            sev_color = "🔴" if severity == "high" else ("🟡" if severity == "medium" else "🟢")

            with st.expander(f"{sev_color} {master_zh} — {q_count} 題，日期: {date}", expanded=False):

                # Show related master_opinions
                if not df_masters.empty and "challenge_id" in df_masters.columns:
                    challenge_opinions = df_masters[df_masters.get("challenge_id") == challenge_id]
                else:
                    challenge_opinions = df_masters[
                        (df_masters["master_name"] == master_zh) if "master_name" in df_masters.columns else [False]
                    ]

                if not challenge_opinions.empty:
                    for _, op in challenge_opinions.iterrows():
                        ticker = op.get("stock_ticker", "")
                        question = op.get("question", "")
                        opinion = op.get("opinion", "")
                        opinion_severity = op.get("severity", "")

                        op_sev_color = "🔴" if opinion_severity == "high" else ("🟡" if opinion_severity == "medium" else "🟢")

                        st.markdown(f"**{op_sev_color} [{ticker}] {question}**")
                        st.markdown(f"> {opinion}")
                        st.markdown("---")
                else:
                    st.info("尚無此挑戰的詳細觀點記錄")

    else:
        st.info("尚無大師挑戰記錄。點擊上方按鈕啟動挑戰。")

# ============================================================================
# FOOTER
# ============================================================================
st.markdown("---")
st.caption(
    "10-Bagger Agent System v3.1 | 戰情儀表板 | "
    "v7 六維度計分 | Supabase + n8n + NotebookLM + Streamlit | "
    f"最後更新: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
)
