"""
pages/1_Jobs.py
Jobs management page.
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import streamlit as st

from services.database import fetch_all, fetch_one, execute

if not st.session_state.get("logged_in"):
    st.warning("Please login first.")
    st.stop()

st.set_page_config(page_title="Jobs", layout="wide")

css_path = BASE_DIR / "assets" / "style.css"
if css_path.exists():
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown(
    """
    <div class="page-header">
        <h1>Jobs</h1>
        <p>Manage job postings and requirements</p>
    </div>
    """,
    unsafe_allow_html=True,
)

tab1, tab2 = st.tabs(["All Jobs", "Create Job"])

with tab1:
    try:
        jobs = fetch_all("""
            SELECT j.id, j.title, j.description, j.required_skills,
                   j.minimum_experience, j.created_at,
                   u.name AS created_by_name,
                   (SELECT COUNT(*) FROM resumes WHERE job_id = j.id) AS applicant_count,
                   (SELECT AVG(resume_score) FROM predictions WHERE job_id = j.id) AS avg_score
            FROM jobs j
            LEFT JOIN users u ON u.id = j.created_by
            ORDER BY j.created_at DESC
        """)
    except Exception as e:
        st.error(f"Failed to load jobs: {e}")
        jobs = []

    if not jobs:
        st.markdown(
            '<div class="empty-state">No jobs yet.<br>'
            'Switch to "Create Job" tab to add one.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="section-subtitle">{len(jobs)} job postings</div>',
            unsafe_allow_html=True,
        )

        for job in jobs:
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.markdown(f"### {job['title']}")
                    st.caption(
                        f"Minimum experience: {job['minimum_experience']} years  |  "
                        f"Posted by: {job['created_by_name'] or 'System'}"
                    )

                    skills = [
                        s.strip()
                        for s in (job["required_skills"] or "").split(",")
                        if s.strip()
                    ]
                    if skills:
                        st.markdown(
                            "**Required skills:** "
                            + " ".join([f"`{s}`" for s in skills])
                        )

                    with st.expander("View description"):
                        st.write(job["description"] or "N/A")

                with col2:
                    st.metric("Applicants", job["applicant_count"])
                    avg = job["avg_score"]
                    st.metric("Avg Score", f"{avg:.1f}" if avg else "—")

                st.caption(f"Posted: {job['created_at']}")

with tab2:
    st.markdown(
        '<div class="section-title">Create a new job</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-subtitle">Fill in the details below</div>',
        unsafe_allow_html=True,
    )

    with st.form("create_job_form", clear_on_submit=False):
        title = st.text_input("Job title", placeholder="Machine Learning Engineer")
        description = st.text_area(
            "Job description",
            placeholder="Describe role, responsibilities, expectations...",
            height=160,
        )
        required_skills = st.text_area(
            "Required skills (comma-separated)",
            placeholder="Python, Machine Learning, NLP, SQL, TensorFlow",
            height=80,
        )
        minimum_experience = st.number_input(
            "Minimum experience (years)",
            min_value=0, max_value=30, value=1, step=1,
        )

        submitted = st.form_submit_button("Create job", use_container_width=True)

    if submitted:
        errors = []
        if not title or not title.strip():
            errors.append("Job title is required.")
        if not description or not description.strip():
            errors.append("Job description is required.")
        if not required_skills or not required_skills.strip():
            errors.append("At least one required skill is needed.")

        if errors:
            for err in errors:
                st.error(err)
        else:
            try:
                skills_clean = ", ".join(
                    [s.strip() for s in required_skills.split(",") if s.strip()]
                )
                user_row = fetch_one(
                    "SELECT id FROM users WHERE email = :e",
                    {"e": st.session_state.user["email"]},
                )
                created_by = user_row["id"] if user_row else None

                execute(
                    """INSERT INTO jobs
                       (title, description, required_skills,
                        minimum_experience, created_by)
                       VALUES (:t, :d, :rs, :me, :cb)""",
                    {
                        "t": title.strip(),
                        "d": description.strip(),
                        "rs": skills_clean,
                        "me": int(minimum_experience),
                        "cb": created_by,
                    },
                )

                st.success(f"Job '{title}' created successfully.")
                st.info("Switch to 'All Jobs' tab to see it.")

            except Exception as e:
                st.error(f"Failed to create job: {e}")