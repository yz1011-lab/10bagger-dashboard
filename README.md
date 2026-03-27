# 10-Bagger Agent System — Streamlit Dashboard v3.1

Multi-Agent 股票分析系統的戰情儀表板前端。

## 功能（8 個分頁）

| 分頁 | 功能 |
|------|------|
| 📋 選股追蹤 | v7 六維度計分、賽道權重圓餅圖、市場/賽道篩選、個股詳情（分數拆解圖、P(H) 儀表、大師即時分析、Yahoo 新聞） |
| 📈 機率變化 | 全股 P(H) 橫條圖、時序趨勢折線圖、Bull/Bear/Judge 辯論卡片、Bayesian 更新追蹤 |
| 🔍 稽核報告 | Spearman Rho 趨勢圖、殭屍股數、信號燈號、最新報告 JSON 詳情 |
| 🏆 大師看法 | 6 位投資大師觀點（巴菲特、蒙格、馬克斯、提爾、科斯托蘭尼、林區）、按大師分組、嚴重性標示 |
| 📰 最新資訊 | 證據記錄、賽道研究摘要（催化劑+風險）、決策信箱（通過/駁回） |
| 📚 資料來源 | NotebookLM 知識來源總覽、賽道/個股 NLM 狀態 |
| 📖 知識庫管理 | NotebookLM Sources CRUD（新增/刪除來源） |
| 🎓 大師挑戰 | 全大師批次挑戰 via n8n webhook、歷史挑戰結果 |

## v7 六維度計分權重

- 毛利率 GM: 15%
- 營收成長 Rev: 20%
- 市值甜蜜點 MCap: 15%
- 多年一致性 Cons: 15%
- 賽道相關性 Track: 20%
- 動能評分 Mom: 15%

## 技術棧

Python + Streamlit + Supabase REST API + Plotly + Yahoo Finance RSS

## 部署

1. Fork / clone 此 repo
2. 在 Streamlit Cloud 連結 GitHub repo
3. 設定 Main file path: `app.py`
4. 在 Advanced settings → Secrets 中貼入 `secrets.toml.example` 的內容並填入實際值

## 本地開發

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# 填入實際的 Supabase key 和 n8n webhook
streamlit run app.py
```
