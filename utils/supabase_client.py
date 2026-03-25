"""Supabase client singleton for the 10-Bagger dashboard."""

import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def get_supabase() -> Client:
    """Return a cached Supabase client instance."""
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


# ---------------------------------------------------------------------------
# Query helpers (all return list[dict])
# ---------------------------------------------------------------------------

def fetch_active_stocks() -> list[dict]:
    """Fetch all active stocks."""
    sb = get_supabase()
    res = sb.table("active_stocks").select("*").eq("status", "active").execute()
    return res.data or []


def fetch_stock_probabilities() -> list[dict]:
    sb = get_supabase()
    res = sb.table("stock_probabilities").select("*").execute()
    return res.data or []


def fetch_probability_log(ticker: str | None = None, limit: int = 200) -> list[dict]:
    sb = get_supabase()
    q = sb.table("probability_log").select("*").order("created_at", desc=True).limit(limit)
    if ticker:
        q = q.eq("stock_ticker", ticker)
    return q.execute().data or []


def fetch_evidence_log(ticker: str | None = None, limit: int = 100) -> list[dict]:
    sb = get_supabase()
    q = sb.table("evidence_log").select("*").order("created_at", desc=True).limit(limit)
    if ticker:
        q = q.eq("stock_ticker", ticker)
    return q.execute().data or []


def fetch_tracks() -> list[dict]:
    sb = get_supabase()
    res = sb.table("tracks").select("*").order("confidence", desc=True).execute()
    return res.data or []


def fetch_notebook_sources(ticker: str | None = None) -> list[dict]:
    sb = get_supabase()
    q = sb.table("notebook_sources").select("*").order("created_at", desc=True)
    if ticker:
        q = q.eq("ticker", ticker)
    return q.execute().data or []


def update_notebook_source_status(source_id: int, status: str) -> None:
    sb = get_supabase()
    sb.table("notebook_sources").update({"status": status}).eq("id", source_id).execute()


def fetch_decisions_inbox(status: str | None = None) -> list[dict]:
    sb = get_supabase()
    q = sb.table("decisions_inbox").select("*").order("created_at", desc=True)
    if status:
        q = q.eq("status", status)
    return q.execute().data or []


def fetch_master_challenges(limit: int = 50) -> list[dict]:
    """Fetch master challenge history (table may not exist yet)."""
    sb = get_supabase()
    try:
        res = (
            sb.table("master_challenges")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception:
        return []


def fetch_agents_config() -> list[dict]:
    sb = get_supabase()
    res = sb.table("agents_config").select("*").execute()
    return res.data or []
