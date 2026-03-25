# 10-Bagger Agent System — Streamlit Dashboard v2

Multi-Agent 股票分析系統的戰情儀表板前端。

## 頁面

| 頁面 | 功能 |
|------|------|
| 🏠 戰情總覽 | KPI、全股票 P(H) 儀表板、走勢圖、賽道信心 |
| 📊 個股詳情 | 個股 P(H)、NotebookLM 連結、證據記錄、貝葉斯更新明細 |
| 🧪 貝葉斯分析 | 全股比較、Bull/Bear/Judge 辯論明細、證據時間軸 |
| 📚 知識庫管理 | NotebookLM Sources CRUD、按股票分頁管理 |
| 🎓 大師挑戰 | 6 位投資大師辯論、n8n webhook 觸發、結果展開 |
| 🛤️ 賽道與決策 | 賽道信心指數、決策信箱通過/駁回 |

## 技術棧

Python + Streamlit + Supabase + Plotly

## 部署

1. Fork / clone 此 repo
2. 在 [Streamlit Cloud](https://share.streamlit.io) 連結 GitHub repo
3. 設定 Main file path: `app.py`
4. 在 Advanced settings → Secrets 中貼入 `secrets.toml.example` 的內容並填入實際值

## 本地開發

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# 填入實際的 Supabase key
streamlit run app.py
```
