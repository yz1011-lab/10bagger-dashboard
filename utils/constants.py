"""Shared constants for the 10-Bagger dashboard."""

# ---------- Investment Masters ----------
MASTERS = {
    "buffett": {
        "name": "巴菲特",
        "en": "Warren Buffett",
        "icon": "🏛️",
        "philosophy": "能力圈・護城河",
        "description": "專注於企業內在價值與持久競爭優勢",
    },
    "thiel": {
        "name": "彼得提爾",
        "en": "Peter Thiel",
        "icon": "🚀",
        "philosophy": "從0到1・壟斷思維",
        "description": "尋找具壟斷特質的創新型企業",
    },
    "lynch": {
        "name": "彼得林區",
        "en": "Peter Lynch",
        "icon": "🛒",
        "philosophy": "生活選股・PEG",
        "description": "從日常生活中發現投資機會",
    },
    "kostolany": {
        "name": "科斯托蘭尼",
        "en": "André Kostolany",
        "icon": "🎭",
        "philosophy": "資金+心理・反群眾",
        "description": "重視市場心理與資金流動",
    },
    "munger": {
        "name": "查理蒙格",
        "en": "Charlie Munger",
        "icon": "🧠",
        "philosophy": "多元思維・反向思考",
        "description": "跨學科思維模型解構投資決策",
    },
    "marks": {
        "name": "霍華馬克斯",
        "en": "Howard Marks",
        "icon": "🔄",
        "philosophy": "第二層思考・週期",
        "description": "關注市場週期與非共識投資機會",
    },
}

# ---------- Probability thresholds ----------
PH_ELIMINATION = 0.05
PH_HIGH_PROBABILITY = 0.50
PH_INITIAL = 0.15
CLAMP_RATIO = 0.30

# ---------- Alert type labels ----------
ALERT_LABELS = {
    "none": ("—", "gray"),
    "low_probability": ("⚠️ 低機率", "red"),
    "high_probability": ("🔥 高機率", "green"),
    "volatility": ("📊 高波動", "orange"),
    "low_probability+volatility": ("⚠️📊 低機率+波動", "red"),
    "high_probability+volatility": ("🔥📊 高機率+波動", "green"),
}

# ---------- Consensus level colors ----------
CONSENSUS_COLORS = {
    "high": "#22c55e",
    "moderate": "#eab308",
    "contrarian": "#ef4444",
}

# ---------- Google Drive / NotebookLM ----------
DRIVE_FOLDERS = {
    "root": "1PV-m_i1xgvgzneI9CJgoezR4r-Arf0Rk",
    "01_macro": "1kuzbq5iMqtgQWU9tJclhNjSaVfeXh9g4",
    "02_stocks": "1fmy8HHZmZOaPHhmpthfawyrCei7M8918",
    "03_market": "1NqAEF4n34Cm_iuubwhMJ-b41TsRkIZMe",
    "04_audit": "17Op5Jrf7ILSiDIZKXSjWMciKpkN1w7-K",
}

NOTEBOOKLM_BASE = "https://notebooklm.google.com/notebook"
