import html
import os
import asyncio

import streamlit as st

from jobhunter_engine import search_jobs

st.set_page_config(page_title="JobHunter", page_icon="🔍", layout="centered")

# ── Config ──
GITHUB_REPO = os.getenv("GITHUB_REPO_URL", "https://github.com/atharva-todmal/jobhunter")
SOURCE_COLORS = {
    "Talent": "#3B82F6",
    "Dice": "#8B5CF6",
    "LinkedIn": "#0077B5",
    "Adzuna": "#06B6D4",
    "Jooble": "#10B981",
    "Unknown": "#6B7280",
}

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    * {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important; }}

    .stApp {{
        background: #080808;
    }}
    .block-container {{
        max-width: 720px;
        padding-top: 2.5rem !important;
    }}
    h1, h2, h3, h4, h5, p, li, .stMarkdown {{
        color: #e8e8e8 !important;
    }}
    a {{
        color: #7C6FFF !important;
        text-decoration: none;
    }}
    a:hover {{
        text-decoration: underline;
    }}

    /* ── Header ── */
    .header-wrap {{
        text-align: center;
        margin-bottom: 0.125rem;
    }}
    .title-main {{
        font-size: 2.25rem;
        font-weight: 700;
        background: linear-gradient(135deg, #7C6FFF, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: -0.75px;
        margin: 0;
        line-height: 1.2;
    }}
    .header-sub {{
        color: #777;
        font-size: 0.82rem;
        margin-top: 0;
        margin-bottom: 0.4rem;
    }}
    .header-sub strong {{
        color: #a78bfa;
        font-weight: 600;
    }}
    .header-github {{
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        background: rgba(124,111,255,0.08);
        color: #a78bfa !important;
        font-size: 0.75rem;
        padding: 0.3rem 0.8rem;
        border-radius: 6px;
        text-decoration: none !important;
        transition: background 0.2s;
        margin-bottom: 1.75rem;
    }}
    .header-github:hover {{
        background: rgba(124,111,255,0.15);
    }}

    /* ── Input row ── */
    div[data-testid="stTextInput"] input {{
        background: #111 !important;
        border: 1px solid #222 !important;
        border-radius: 10px !important;
        color: #e8e8e8 !important;
        padding: 0.75rem 1rem !important;
        font-size: 0.95rem !important;
    }}
    div[data-testid="stTextInput"] input:focus {{
        border-color: #7C6FFF !important;
        box-shadow: 0 0 0 2px rgba(124,111,255,0.12) !important;
    }}
    div[data-testid="stTextInput"] input::placeholder {{
        color: #444 !important;
        font-size: 0.85rem !important;
    }}
    div[data-testid="stTextInput"] label {{
        display: none !important;
    }}
    div.stButton button[kind="primary"] {{
        background: #7C6FFF !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.7rem 1.5rem !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        color: #fff !important;
        height: 46px;
        transition: background 0.15s !important;
    }}
    div.stButton button[kind="primary"]:hover {{
        background: #6a5ee6 !important;
    }}

    /* ── Status bar ── */
    .status-bar {{
        display: flex;
        align-items: center;
        gap: 0.6rem;
        flex-wrap: wrap;
        margin-bottom: 1.25rem;
    }}
    .status-count {{
        display: inline-block;
        background: rgba(124,111,255,0.1);
        color: #a78bfa;
        padding: 0.3rem 0.9rem;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 600;
    }}
    .status-sources {{
        display: flex;
        gap: 0.35rem;
        flex-wrap: wrap;
    }}
    .mini-badge {{
        font-size: 0.68rem;
        font-weight: 600;
        padding: 0.15rem 0.5rem;
        border-radius: 4px;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }}

    /* ── Job card ── */
    .job-card {{
        background: #111;
        border: 1px solid #1e1e1e;
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 0.85rem;
        transition: border-color 0.2s;
    }}
    .job-card:hover {{
        border-color: #333;
    }}
    .job-card .card-head {{
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.5rem;
    }}
    .job-card .card-source-badge {{
        font-size: 0.6rem;
        font-weight: 700;
        padding: 0.15rem 0.5rem;
        border-radius: 4px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        flex-shrink: 0;
    }}
    .job-card h3 {{
        margin: 0 0 0.15rem 0 !important;
        font-size: 1.05rem !important;
        font-weight: 600 !important;
        color: #f0f0f0 !important;
        line-height: 1.35;
    }}
    .job-card .company {{
        color: #999;
        font-size: 0.85rem;
        margin-bottom: 0.65rem;
    }}
    .job-card .company strong {{
        color: #bbb;
        font-weight: 500;
    }}
    .job-card .meta {{
        display: flex;
        flex-wrap: wrap;
        gap: 0.35rem 1rem;
        font-size: 0.8rem;
        color: #666;
        margin-bottom: 0.85rem;
    }}
    .job-card .meta span {{
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
    }}
    .job-card .apply-link {{
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        background: #7C6FFF;
        color: #fff !important;
        padding: 0.4rem 1rem;
        border-radius: 8px;
        font-size: 0.82rem;
        font-weight: 500;
        text-decoration: none !important;
        transition: background 0.15s;
    }}
    .job-card .apply-link:hover {{
        background: #6a5ee6;
    }}

    /* ── Load more ── */
    div.stButton button[kind="secondary"] {{
        background: transparent !important;
        border: 1px solid #222 !important;
        border-radius: 10px !important;
        color: #888 !important;
        padding: 0.45rem 0 !important;
        font-size: 0.85rem !important;
        transition: all 0.2s !important;
        width: 100%;
    }}
    div.stButton button[kind="secondary"]:hover {{
        border-color: #7C6FFF !important;
        color: #7C6FFF !important;
    }}

    /* ── Empty / initial state ── */
    .empty-state {{
        text-align: center;
        padding: 3.5rem 0;
        color: #555;
    }}
    .empty-state .icon {{
        font-size: 2.25rem;
        margin-bottom: 0.5rem;
    }}
    .empty-state p {{
        color: #555 !important;
        font-size: 0.9rem;
    }}
    .empty-state .hint {{
        color: #444 !important;
        font-size: 0.8rem;
        margin-top: 0.25rem;
    }}

    /* ── Warning / validation ── */
    .stAlert {{
        background: rgba(124,111,255,0.05) !important;
        border: 1px solid rgba(124,111,255,0.15) !important;
        border-radius: 8px !important;
        color: #a78bfa !important;
        font-size: 0.85rem !important;
        padding: 0.5rem 1rem !important;
    }}

    /* ── Footer ── */
    .footer {{
        text-align: center;
        margin-top: 3.5rem;
        padding-top: 1.5rem;
        border-top: 1px solid #181818;
    }}
    .footer .credit {{
        color: #555;
        font-size: 0.8rem;
        margin-bottom: 0.3rem;
    }}
    .footer .credit strong {{
        color: #a78bfa;
        font-weight: 600;
    }}
    .footer .links {{
        display: flex;
        justify-content: center;
        gap: 1rem;
        font-size: 0.75rem;
    }}
    .footer .links a {{
        color: #555 !important;
        text-decoration: none !important;
        transition: color 0.15s;
    }}
    .footer .links a:hover {{
        color: #a78bfa !important;
    }}
    .footer .copy {{
        color: #333;
        font-size: 0.7rem;
        margin-top: 0.5rem;
    }}
</style>
""", unsafe_allow_html=True)

# ── Header ──
st.markdown(
    '<div class="header-wrap">'
    '<h1 class="title-main">JobHunter</h1>'
    '<p class="header-sub">Crafted by <strong>Atharva Todmal</strong></p>'
    f'<a class="header-github" href="{GITHUB_REPO}" target="_blank" rel="noopener">'
    "&#9733; Star on GitHub</a>"
    "</div>",
    unsafe_allow_html=True,
)

# ── Search row ──
col_in, col_btn = st.columns([4, 1])
with col_in:
    query = st.text_input(
        "keywords",
        placeholder="e.g. python developer, data analyst...",
        label_visibility="collapsed",
    )
with col_btn:
    search_clicked = st.button("Search", type="primary", use_container_width=True)

# ── Initialise session state ──
if "all_jobs" not in st.session_state:
    st.session_state.all_jobs = None
if "page" not in st.session_state:
    st.session_state.page = 0
if "searched" not in st.session_state:
    st.session_state.searched = False

PAGE_SIZE = 5

# ── Search with validation ──
if search_clicked:
    cleaned = query.strip()
    if len(cleaned) < 2:
        st.warning("Please enter at least 2 characters")
        search_clicked = False
        st.session_state.searched = False
    else:
        with st.spinner("Searching 5 sources..."):
            results = asyncio.run(search_jobs(cleaned))
        st.session_state.all_jobs = results
        st.session_state.page = 0
        st.session_state.searched = True

# ── Display results ──
jobs = st.session_state.all_jobs
searched = st.session_state.searched

if jobs is not None and searched:
    total = len(jobs)

    if total == 0:
        st.markdown(
            '<div class="empty-state">'
            '<div class="icon">🔍</div>'
            "<p>No jobs found — try different keywords</p>"
            '<p class="hint">5 sources searched: Talent · Dice · LinkedIn · Adzuna · Jooble</p>'
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        # Source breakdown
        source_counts = {}
        for j in jobs:
            s = j.get("source", "Unknown")
            source_counts[s] = source_counts.get(s, 0) + 1

        source_badges = "".join(
            f'<span class="mini-badge" style="background:rgba({int(SOURCE_COLORS.get(s,"#6B7280")[1:3],16)},{int(SOURCE_COLORS.get(s,"#6B7280")[3:5],16)},{int(SOURCE_COLORS.get(s,"#6B7280")[5:7],16)},0.1);color:{SOURCE_COLORS.get(s,"#6B7280")}">{s} {c}</span>'
            for s, c in sorted(source_counts.items())
        )

        st.markdown(
            '<div class="status-bar">'
            f'<span class="status-count">&#10022; {total} jobs</span>'
            '<span class="status-sources">' + source_badges + "</span>"
            "</div>",
            unsafe_allow_html=True,
        )

        start = st.session_state.page * PAGE_SIZE
        end = min(start + PAGE_SIZE, total)
        page_jobs = jobs[start:end]

        for job in page_jobs:
            source = job.get("source", "Unknown")
            safe_title = html.escape(job.get("title", ""))
            safe_company = html.escape(job.get("company", "Unknown"))
            safe_email = html.escape(job.get("email", ""))
            safe_phone = html.escape(job.get("phone", ""))
            raw_link = job.get("link", "")
            safe_link = raw_link if raw_link.startswith(("http://", "https://")) else "#"
            color = SOURCE_COLORS.get(source, "#6B7280")
            r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)

            st.markdown(
                f'<div class="job-card">'
                f'<div class="card-head">'
                f'<span class="card-source-badge" style="background:rgba({r},{g},{b},0.12);color:{color}">{source}</span>'
                f"</div>"
                f"<h3>{safe_title}</h3>"
                f'<div class="company"><strong>{safe_company}</strong></div>'
                f'<div class="meta">'
                f'<span>&#9993; {safe_email}</span>'
                f'<span>&#9742; {safe_phone}</span>'
                f"</div>"
                f'<a class="apply-link" href="{safe_link}" target="_blank" rel="noopener">'
                f"Apply Here &rarr;</a>"
                f"</div>",
                unsafe_allow_html=True,
            )

        if end < total:
            if st.button("Load More ↓", key="load_more", type="secondary", use_container_width=True):
                st.session_state.page += 1
                st.rerun()

elif not searched:
    st.markdown(
        '<div class="empty-state">'
        '<div class="icon">&#10024;</div>'
        "<p>Enter a keyword to start searching</p>"
        '<p class="hint">5 sources: Talent · Dice · LinkedIn · Adzuna · Jooble</p>'
        "</div>",
        unsafe_allow_html=True,
    )

# ── Footer ──
st.markdown(
    '<div class="footer">'
    '<p class="credit">Crafted with &#9829; by <strong>Atharva Todmal</strong></p>'
    f'<div class="links">'
    f'<a href="{GITHUB_REPO}" target="_blank" rel="noopener">&#9733; Star on GitHub</a>'
    "</div>"
    '<p class="copy">&copy; 2026 JobHunter &mdash; All job data belongs to their respective sources</p>'
    "</div>",
    unsafe_allow_html=True,
)
