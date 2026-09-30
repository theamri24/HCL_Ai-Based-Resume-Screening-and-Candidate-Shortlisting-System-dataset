"""
pages/3_Candidates.py
Candidate list with search, filter, sort.
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import streamlit as st
import pandas as pd

from services.database import fetch_all

if not st.session_state.get("logged_in"):
    st.warning("Please login first.")
    st.stop()

st.set_page_config(page_title="Candidates", layout="wide")

css_path = BASE_DIR / "assets" / "style.css"
if css_path.exists():
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown(
    """
    <div class="page-header">
        <h1>Candidates</h1>
        <p>Browse, search, and filter screened candidates</p>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    rows = fetch_all("""
        SELECT
            p.id AS pred_id,
            c.id AS candidate_id,
            c.name, c.email, c.phone, c.education, c.experience,
            j.title AS job_title,
            r.original_filename, r.extracted_text,
            p.resume_score, p.skill_match_percentage, p.similarity_score,
            p.matched_skills, p.missing_skills, p.decision, p.created_at
        FROM predictions p
        JOIN candidates c ON c.id = p.candidate_id
        JOIN jobs j ON j.id = p.job_id
        JOIN resumes r ON r.id = p.resume_id
        ORDER BY p.created_at DESC
    """)
except Exception as e:
    st.error(f"Failed to load data: {e}")
    st.stop()

if not rows:
    st.markdown(
        '<div class="empty-state">No candidates yet.<br>'
        'Go to Upload Resume to add one.</div>',
        unsafe_allow_html=True,
    )
    st.stop()

df = pd.DataFrame(rows)

st.markdown('<div class="section-title">Filters</div>',
            unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

with col1:
    search = st.text_input("Search", placeholder="Name or email")
with col2:
    job_titles = ["All"] + sorted(df["job_title"].dropna().unique().tolist())
    job_filter = st.selectbox("Job", job_titles)
with col3:
    decision_options = ["All"] + sorted(df["decision"].dropna().unique().tolist())
    decision_filter = st.selectbox("Decision", decision_options)
with col4:
    sort_by = st.selectbox("Sort by",
                            ["Newest first", "Oldest first",
                             "Highest score", "Lowest score"])

score_min, score_max = st.slider("Score range", 0, 100, (0, 100), step=5)

filtered = df.copy()

if search.strip():
    s = search.strip().lower()
    filtered = filtered[
        filtered["name"].str.lower().str.contains(s, na=False)
        | filtered["email"].str.lower().str.contains(s, na=False)
    ]

if job_filter != "All":
    filtered = filtered[filtered["job_title"] == job_filter]

if decision_filter != "All":
    filtered = filtered[filtered["decision"] == decision_filter]

filtered = filtered[
    (filtered["resume_score"] >= score_min)
    & (filtered["resume_score"] <= score_max)
]

if sort_by == "Newest first":
    filtered = filtered.sort_values("created_at", ascending=False)
elif sort_by == "Oldest first":
    filtered = filtered.sort_values("created_at", ascending=True)
elif sort_by == "Highest score":
    filtered = filtered.sort_values("resume_score", ascending=False)
elif sort_by == "Lowest score":
    filtered = filtered.sort_values("resume_score", ascending=True)

st.markdown(
    f'<div class="section-subtitle">Showing {len(filtered)} of {len(df)} candidates</div>',
    unsafe_allow_html=True,
)

if filtered.empty:
    st.markdown('<div class="empty-state">No candidates match filters.</div>',
                unsafe_allow_html=True)
    st.stop()

for _, row in filtered.iterrows():
    with st.container(border=True):
        c1, c2, c3 = st.columns([3, 2, 2])

        with c1:
            st.markdown(f"### {row['name']}")
            st.caption(f"{row['email']}  |  {row['phone'] or '—'}")

        with c2:
            st.markdown(f"**Job:** {row['job_title']}")
            st.markdown(f"**Education:** {row['education'] or '—'}")
            st.markdown(f"**Experience:** {row['experience']} yrs")

        with c3:
            badge_class = {
                "Shortlisted": "badge-shortlist",
                "Review": "badge-review",
                "Rejected": "badge-reject",
            }.get(row["decision"], "badge-review")
            st.markdown(
                f'<span class="badge {badge_class}">{row["decision"]}</span>',
                unsafe_allow_html=True,
            )
            st.markdown(f"**Score:** {row['resume_score']:.1f} / 100")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Skill Match", f"{row['skill_match_percentage']:.1f}%")
        m2.metric("Similarity", f"{row['similarity_score']:.1f}%")

        matched_count = len(
            [s for s in (row["matched_skills"] or "").split(",") if s.strip()]
        )
        missing_count = len(
            [s for s in (row["missing_skills"] or "").split(",") if s.strip()]
        )
        m3.metric("Matched", matched_count)
        m4.metric("Missing", missing_count)

        with st.expander("View full details"):
            st.markdown(f"**Resume file:** `{row['original_filename']}`")
            st.markdown(f"**Uploaded:** {row['created_at']}")

            colA, colB = st.columns(2)

            with colA:
                st.markdown("**Matched skills**")
                m_skills = [s.strip() for s in (row["matched_skills"] or "").split(",") if s.strip()]
                if m_skills:
                    for s in m_skills:
                        st.markdown(f"- {s.title()}")
                else:
                    st.caption("None")

            with colB:
                st.markdown("**Missing skills**")
                miss_skills = [s.strip() for s in (row["missing_skills"] or "").split(",") if s.strip()]
                if miss_skills:
                    for s in miss_skills:
                        st.markdown(f"- {s.title()}")
                else:
                    st.success("All matched.")

            st.markdown("**Extracted resume text**")
            st.text_area(
                "text",
                value=row["extracted_text"] or "(empty)",
                height=250,
                key=f"resume_{row['pred_id']}",
                label_visibility="collapsed",
            )

st.markdown('<div class="section-title" style="margin-top:32px;">Summary</div>',
            unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total", len(filtered))
c2.metric("Shortlisted", len(filtered[filtered["decision"] == "Shortlisted"]))
c3.metric("In Review", len(filtered[filtered["decision"] == "Review"]))
c4.metric("Rejected", len(filtered[filtered["decision"] == "Rejected"]))

avg = filtered["resume_score"].mean() if not filtered.empty else 0
st.metric("Average Score", f"{avg:.1f} / 100")